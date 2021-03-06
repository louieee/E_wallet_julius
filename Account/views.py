from django.contrib import auth
from django.contrib.auth.decorators import login_required

from Account import custom_auth
from Account.models import User
from django.shortcuts import render, redirect

# Create your views here.
from Account.models import Cache
from E_Wallet.utilities import display, flash, send_verification_mail, lock, open_lock, check_unn_email, check_lock, \
	list_of_fees
from Wallet.models import Wallet


# this view returns the home page
def home(request):
	if request.user.is_authenticated:
		return redirect('dashboard')
	else:
		return redirect('login')


# this view returns the login page
def login(request):
	if request.method == 'POST':
		email = request.POST.get('email')
		password = request.POST.get('password')
		user = User.objects.filter(email=email).first()
		if user is None:
			flash(request, 'You do not have an account with us.', 'warning')
			return redirect('signup')
		if not user.is_active and user.last_login is None:
			send_verification_mail(user.email, 'Account Verification ',
								   'login')
			request.session['email'] = user.email
			flash(request, f"Your Pin is {Cache.get(email)['pin']}", 'info')
			return redirect('verify')
		login_time = check_lock(user)
		if login_time is not None:
			flash(request, f'You have been temporarily blocked! You will be able to login in {login_time}', 'danger')
			return redirect('login')
		user = auth.authenticate(request, username=email, password=password)
		if user:
			auth.login(request, user)
			open_lock(user.email, final=True)
			return redirect('dashboard')
		else:
			flash(request, 'Your password is incorrect!', 'danger')
			lock(request.POST.get('email'))
			return redirect('login')
	display_ = display(request)
	if display_ is not None:
		context = display_
		return render(request, 'Account/login.html', context=context)
	return render(request, 'Account/login.html')


# this view returns signup page
def signup(request):
	context = dict()
	if request.method == 'POST':
		if User.objects.filter(email=request.POST.get('email')).exists():
			flash(request, 'An account already exists with this email address!', 'warning')
			return redirect('signup')
		else:
			details = check_unn_email(email=request.POST.get('email'))
			if details is not None:
				username = ''.join(details)
				user = User.objects.create_user(username=username,
												email=request.POST.get('email'),
												password=request.POST.get('password1'))
				user.first_name = details[0]
				user.last_name = details[1]
				user.save()
				wallet = Wallet.objects.create(user=user)
				wallet.save()
				[wallet.beneficiaries.add(Wallet.objects.get(user__email=f"unn.{i.replace(' ', '')}@unn.edu.ng")) for i
				 in list_of_fees]
				send_verification_mail(user.email, 'Account ',
									   'login')
				request.session['email'] = user.email
				flash(request, f"Your Pin is {Cache.get(user.email)['pin']}", 'info')
				return redirect('verify')
			else:
				flash(request, 'This not a unn email address!', 'danger')
				return redirect('signup')
	display_ = display(request)
	if display_ is not None:
		context.update(display_)
	return render(request, 'Account/signup.html', context=context)


# this view returns the dashboard page
@login_required(login_url='login')
def dashboard(request):
	context = dict()
	user = User.objects.get(id=request.user.id)
	context['wallet'] = user.wallet
	display_ = display(request)
	if display_ is not None:
		context.update(display_)
	return render(request, 'Account/dashboard.html', context=context)


# this view allows one to update their profile picture
@login_required(login_url='login')
def update_image(request):
	if request.method == 'POST':
		image_ = request.FILES.get('user_img')
		request.user.profile_picture = image_
		request.user.save()
		return redirect('dashboard')


# this view returns the edit profile page
@login_required(login_url='login')
def edit_profile(request):
	context = dict()
	if request.method == 'GET':
		display_ = display(request)
		if display_ is not None:
			context.update(display_)
		return render(request, 'Account/edit_profile.html', context=context)


# this view logs one out of their session
@login_required(login_url='login')
def logout(request):
	auth.logout(request)
	return redirect('home')


# this view returns the forgot password page
def forgot_password(request):
	context = dict()
	if request.method == 'GET':
		display_ = display(request)
		if display_ is not None:
			context.update(display_)
		return render(request, 'Account/forgot_password.html', context=context)
	else:
		email = request.POST.get('email')
		user = User.objects.filter(email=email).first()
		if user is not None:
			send_verification_mail(email=email, type_='Password Reset', return_page='reset_password')
			request.session['email'] = user.email
			flash(request, f"Your Pin is {Cache.get(email)['pin']}", 'info')
			return redirect('verify')
		else:
			flash(request, 'You do not have an account with us', 'danger')
			return redirect('signup')


# this view returns the verification page
def enter_key(request):
	email = request.session.get('email', None)
	if email is None:
		flash(request, 'Your session expired!', 'info')
		return redirect('home')
	user = User.objects.filter(email=email).first()
	if user is None:
		flash(request, 'You do not have an account with us!', 'danger')
		return redirect('signup')
	email = user.email
	context = {}
	if request.method == 'GET':
		cache = Cache.get(email)
		if cache is None:
			return redirect('home')
		open_lock(email)
		context['email'] = email
		display_ = display(request)
		if display_ is not None:
			context.update(display_)
		return render(request, 'Account/enter_key.html', context=context)
	if request.method == 'POST':
		token_ = Cache.get(email)
		if token_['pin'] != request.POST.get('token'):
			lock(email, request=request)
			flash(request, 'This token is incorrect!', 'danger')
			request.session['email'] = email
			flash(request, f"Your Pin is {Cache.get(email)['pin']}", 'info')
			return redirect('verify')
		else:
			open_lock(email, final=True)
			user.is_active = True
			user.save()
			if token_['return_page'] == 'reset_password':
				return redirect('reset_password')
			if token_['return_page'] == 'edit_profile':
				user.email = token_['email']
				user.save()
				Cache.delete_(email)
			return redirect(token_['return_page'])


# this view enables one to change their password
@login_required(login_url='login')
def change_password(request):
	if request.method == 'POST':
		user = User.objects.get(id=request.user.id)
		old_password = request.POST.get('old_password')
		new_pass1 = request.POST.get('new_password1')
		new_pass2 = request.POST.get('new_password2')
		if not user.check_password(old_password):
			flash(request, 'Your password is incorrect!', 'danger')
			lock(request.user.email, request)
			flash(request, 'You have put in an incorrect password', 'danger')
			return redirect('login')
		if new_pass1 != new_pass2:
			flash(request, 'The two passwords are not the same!', 'danger')
			return redirect('edit_profile')
		user.set_password(new_pass1)
		user.save()
		flash(request, 'You have successfully changed your password.', 'success')
		return redirect('login')


# this view enables one to reset their password
def reset_password(request):
	context = dict()
	email = request.session.get('email', None)
	if email is None:
		flash(request, 'Your session has expired', 'danger')
		return redirect('reset_password')
	else:
		user = User.objects.filter(email=email).first()
	if user is not None:
		if request.method == 'GET' and Cache.get(user.email) is not None:
			display_ = display(request)
			if display_ is not None:
				context.update(display_)
			return render(request, 'Account/reset_password.html', context=context)
		if request.method == 'POST':
			pass1 = request.POST.get('password1')
			pass2 = request.POST.get('password2')
			if pass1 != pass2:
				flash(request, 'The two passwords are not the same.', 'danger')
				return redirect('reset_password', id_=user.id)
			user.set_password(pass1)
			user.save()
			Cache.delete_(user.email)
			flash(request, 'Your password reset is successful.', 'success')
			return redirect('login')
	else:
		flash(request, 'You do not have an account with us!', 'danger')
		return redirect('signup')


# this view allows one to activate all superusers in the system
def activate_superusers(request):
	if request.method == 'GET':
		User.objects.filter(is_superuser=True).update(is_active=True)
		flash(request, 'Activated Superusers', 'success')
		return redirect('home')
