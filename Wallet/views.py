import json
from decimal import Decimal

from django.contrib import auth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.utils.datetime_safe import date

from Account.models import User, Card, Source
from E_Wallet.utilities import display, flash, lock, banks
from Wallet.models import Transaction, Wallet


def deposit(request):
    context = dict()
    if request.method == 'GET':
        display_ = display(request)
        if display_ is not None:
            context = display_
        return render(request, 'Wallet/deposit.html', context=context)
    if request.method == 'POST':
        pass


def transfer(request):
    context = dict()
    wallet = Wallet.objects.get(user_id=request.user.id)
    if request.method == 'GET':
        context['beneficiaries'] = wallet.beneficiaries.all()
        display_ = display(request)
        if display_ is not None:
            context.update(display_)
        return render(request, 'Wallet/transfer.html', context)
    if request.method == 'POST':
        beneficiary_id = request.POST.get('ben')
        amount = request.POST.get('amount')
        password = request.POST.get('password')
        if wallet.user.check_password(password):
            Transaction.objects.create(
                amount=Decimal(amount), type=Transaction.Choice.transfer, sender=wallet,
                receiver_id=int(beneficiary_id), status=Transaction.Choice.success)
            flash(request, 'Transfer Successful', 'success')
            return redirect('dashboard')
        else:
            lock(email=wallet.user.email, request=request)
            flash(request, 'The password is incorrect', 'danger')
            return redirect('login')


def withdraw(request):
    context = dict()
    wallet = Wallet.objects.get(user_id=request.user.id)
    if request.method == 'GET':
        context['banks'] = banks
        context['sources'] = wallet.user.withdrawal_channels()
        display_ = display(request)
        if display_ is not None:
            context.update(display_)
        return render(request, 'Wallet/withdraw.html', context)
    if request.method == 'POST':
        bank = request.POST.get('bank')
        acct_num = request.POST.get('acct_num')
        amount = request.POST.get('amount')
        password = request.POST.get('password')
        source_id = request.POST.get('source_id', None)
        if not wallet.user.check_password(password):
            lock(wallet.user.email)
            flash(request, 'You entered an incorrect password', 'danger')
            return redirect('login')
        if source_id is not '':
            source = Source.objects.get(id=int(source_id))
        else:
            source = Source.objects.filter(channel=Source.Choice.bank, type=Source.Choice.withdrawal,
                                               bank_name=bank, account_number=acct_num, wallet_id=wallet.id).first()
            if source is None:
                source = Source.objects.create(type=Source.Choice.withdrawal, channel=Source.Choice.bank, bank_name=bank,
                                                   account_number=acct_num, wallet_id=wallet.id)

        Transaction.objects.create(amount=Decimal(amount), type=Transaction.Choice.withdrawal,
                              status=Transaction.Choice.success, source=source, sender=wallet)
        flash(request, 'Withdrawal is successful', 'success')
        return redirect('dashboard')


def transactions(request):
    context = dict()
    type_ = request.GET['type']
    context['type'] = type_
    context['bank'] = False
    if type_ == 'withdrawal' or type_ == 'deposit':
        context['bank'] = True
    wallet = Wallet.objects.filter(user_id=request.user.id).first()
    if wallet is None:
        auth.logout(request)
        return redirect('login')
    if type_ == 'withdrawal':
        context['transactions'] = wallet.withdrawal_transactions()
    elif type_ == 'deposit':
        context['transactions'] = wallet.deposit_transactions()
    elif type_ == 'in_transfer':
        context['transactions'] = wallet.received_transfers()
    else:
        context['transactions'] = wallet.transfer_transactions()
    display_ = display(request)
    if display_ is not None:
        context.update(display_)
    return render(request, 'Wallet/transactions.html', context=context)


def beneficiaries(request):
    context = dict()
    if request.method == 'GET':
        beneficiaries_ = Wallet.objects.get(user_id=request.user.id).beneficiaries.all()
        context['beneficiaries'] = beneficiaries_
        display_ = display(request)
        if display_ is not None:
            context.update(display_)
        return render(request, 'Wallet/beneficiaries.html', context=context)


def cards(request):
    if request.method == 'GET':
        context = dict()
        cards_ = User.objects.get(id=request.user.id).cards()
        context['cards'] = cards_
        display_ = display(request)
        if display_ is not None:
            context.update(display_)
        return render(request, 'Wallet/cards.html', context=context)


def add_beneficiary(request):
    context = dict()
    if request.method == 'GET':
        display_ = display(request)
        if display_ is not None:
            context.update(display_)
        return render(request, 'Wallet/add_beneficiary.html', context)
    if request.method == 'POST':
        email = request.POST.get('email')
        wallet = Wallet.objects.filter(user__email=email).first()
        if wallet is None:
            flash(request, 'This email does not belong to any account', 'info')
            return redirect('add_beneficiary')
        else:
            my_wallet = Wallet.objects.get(user_id=request.user.id)
            my_wallet.beneficiaries.add(wallet)
            my_wallet.save()
            flash(request, 'Beneficiary added successfully', 'success')
            return redirect('beneficiaries')


def add_card(request):
    context = dict()
    if request.method == 'GET':
        display_ = display(request)
        if display_ is not None:
            context.update(display_)
        return render(request, 'Wallet/add_card.html', context)
    if request.method == 'POST':
        pin = request.POST.get('pin')
        cvv = request.POST.get('cvv')
        expiry = request.POST.get('expiry')
        expiry_date = str(expiry).split('-')
        expiry_date = date(year=int(expiry_date[0]), month=int(expiry_date[1]), day=int(expiry_date[2]))
        card = Card.objects.filter(first_digits=str(pin)[:4], last_digits=str(pin)[-4:],
                                   cvv=str(cvv), expiry_date=expiry_date).exists()
        wallet = Wallet.objects.get(user_id=request.user.id)
        if card:
            flash(request, 'This card is owned by another user', 'danger')
            return redirect('add_card')
        else:
            Card.objects.create(wallet_id=wallet.id, first_digits=str(pin)[:4], last_digits=str(pin)[-4:],
                                cvv=str(cvv), expiry_date=expiry_date)
            return redirect('cards')


# list of fucking apis

def delete_card(request):
    if request.method == 'POST':
        id_ = request.POST.get('secret_value')
        Card.objects.filter(id=int(id_)).delete()
        flash(request, 'Card deleted successfully', 'success')
        return redirect('cards')


def make_deposit_api(request):
    pass


def make_withdrawal_api(request):
    pass


def make_transfer_api(request):
    pass


def delete_beneficiary(request):
    if request.method == 'POST':
        id_ = request.POST.get('secret_value')
        wallet = Wallet.objects.get(id=int(id_))
        my_wallet = Wallet.objects.get(user_id=request.user.id)
        my_wallet.beneficiaries.remove(wallet)
        flash(request, 'Beneficiary removed successfully', 'success')
        return redirect('beneficiaries')


def get_beneficiary(request):
    if request.method == 'GET':
        id_ = request.GET.get('ben_id')
        wallet = Wallet.objects.filter(id=int(id_)).first()
        if wallet is not None:
            return JsonResponse({
                "full_name": wallet.owner(),
                "email": wallet.user.email
            })
        return JsonResponse({})


def get_account_balance(request):
    if request.method == 'GET':
        wallet = Wallet.objects.get(user_id=request.user.id)
        return HttpResponse(wallet.account_balance())


def get_source(request):
    id_ = request.GET.get('source_id')
    source = Source.objects.filter(id=id_).first()
    if source is None:
        return JsonResponse({})
    return JsonResponse({
        "bank": source.bank_name,
        "account_number": source.account_number
    })