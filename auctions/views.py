from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseBadRequest
from django.urls import reverse
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from datetime import datetime
from django.utils.timezone import now
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from .models import Listing
from .models import User, Listing, Bidding, Watchlist, Closebid, Comment, Category
from .forms import ListingForm, BiddingForm, CommentForm
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.conf import settings
from django.contrib.auth import get_user_model
import random
import string
import boto3
from botocore.exceptions import ClientError


def send_email(recipient_list, subject, message, html_message=None, region_name="us-east-1"):
    client = boto3.client('ses', region_name=region_name)
    charset = "UTF-8"
    sender = "noreply@soulisto.com.br"
        
    destination = {
        'ToAddresses': recipient_list,
    }
        
    body = {
        'Text': {
            'Charset': charset,
            'Data': message,
        },
        'Html': {
            'Charset': charset,
            'Data': html_message,
        },
    }
        
    email_message = {
        'Subject': {
            'Charset': charset,
            'Data': subject,
        },
        'Body': body,
    }
        
    try:
        response = client.send_email(
            Destination=destination,
            Message=email_message,
            Source=sender,
        )
        return response['MessageId']
    except Exception as e:
        print("Email sending failed: ", str(e))


User = get_user_model()

def index(request):
    listing = Listing.objects.all()
    category = request.GET.get('category')
    search_query = request.GET.get('q')
    if category:
        listing = listing.filter(category=category)
    if search_query:
        if search_query.isdigit():
            listing = listing.filter(id=search_query)
        else:
            listing = listing.filter(title__icontains=search_query)
    try:
        watch = Watchlist.objects.filter(watcher=request.user.username)
        watchcount = len(watch)
    except:
        watchcount = None

    return render(request, "auctions/index.html", {
        'object': listing,
        'watchcount': watchcount,
        'search_query': search_query
    })




@login_required
def createlisting(request):
    creator = Listing.objects.all()
    form = ListingForm(request.POST or None)
    try:
        watch = Watchlist.objects.filter(watcher=request.user.username)
        watchcount = len(watch)
    except:
        watchcount = None
    if request.method == "POST":
        if form.is_valid():
            now = datetime.now()  # save date created with current timezone
            fs = form.save(commit=False)
            fs.lister = request.user.email  # save info not listed at forms.py
            fs.created = now
            fs.save()
        return HttpResponseRedirect(reverse('index'))
    else:
        return render(request, "auctions/create.html", {
            'form': form,
            'creator': creator,
            'watchcount': watchcount
        })


def listingpage(request, id):
    listing = Listing.objects.get(id=id)
    comment = Comment.objects.filter(listingid=id)
    try:
        cform = CommentForm(request.POST or None)
        bidform = BiddingForm(request.POST or None, initial={'bidprice': listing.startingbids+5})
    except:
        return redirect('index')
    if request.user.username:
        try:
            if Watchlist.objects.get(watcher=request.user.username, listingid=id):
                added = True
        except:
            added = False
        try:
            watch = Watchlist.objects.filter(watcher=request.user.username)
            watchcount = len(watch)
        except:
            watchcount = None
        try:
            ccount = Comment.objects.filter(listingid=id)
            ccount = len(ccount)
        except:
            ccount = len(ccount)
        try:

            if listing.lister == request.user.username:
                lister = True
            else:
                lister = False
        except:
            return redirect('index')
    else:
        ccount = Comment.objects.filter(listingid=id)
        ccount = len(ccount)
        added = False
        lister = False
        watchcount = None
    try:
        bid = Bidding.objects.filter(listingid=id)
        bidcount = len(bid)
        listing = Listing.objects.get(id=id)
    except:
        bicount = None
    return render(request, "auctions/listing.html", {
        'object': listing,
        'added': added,
        'bidform': bidform,
        "watchcount": watchcount,
        "error": request.COOKIES.get('error'),
        "success": request.COOKIES.get('success'),
        "bidcount": bidcount,
        "lister": lister,
        'cform': cform,
        "comment": comment,
        "ccount": ccount
    })


@login_required
def addwatch(request, id):
    if request.user.username:
        listing = Listing.objects.get(id=id)
        watchers = Watchlist(watcher=request.user.username, listingid=id)
        watchers.lister = listing.lister
        watchers.finalbid = listing.startingbids
        watchers.productnames = listing.productnames
        watchers.images = listing.images
        watchers.save()
        return redirect('listingpage', id=id)
    else:
        return redirect('index')


@login_required
def removewatch(request, id):
    if request.user.username:
        try:
            Watchlist.objects.filter(listingid=id).delete()
            return redirect('listingpage', id=id)
        except:
            return redirect('listingpage', id=id)
    else:
        return redirect('index')


@login_required
def watchlist(request):
    try:
        watchlist = Watchlist.objects.filter(watcher=request.user.username)
        mybids = Bidding.objects.filter(bidder=request.user.email)
        closebid = Closebid.objects.filter(bidder=request.user.email)
        # count how many rows in table Watchlist using len()
        watchcount = len(watchlist)
        mybidcount = len(mybids)
    except:
        watchcount = None
        mybidcount = None
    try:
        bidwincount = Closebid.objects.filter(bidder=request.user.email)
        bidwincount = len(bidwincount)
    except:
        bidwincount = None
    try:
        if Watchlist.objects.get(listingid=listingid):
            closed = True
        if Bidding.objects.get(listingid=listingid):
            closed = True
        else:
            closed = False
    except:
        closed = False
    return render(request, "auctions/watchlist.html", {
        'object': watchlist,
        "watchcount": watchcount,
        "closedbid": closebid,
        "closed": closed,
        "bidwincount": bidwincount,
        'mybids': mybids,
        "mybidcount": mybidcount,
    })


@login_required
def bid(request, listingid):
    current = Listing.objects.get(id=listingid)
    current = current.startingbids
    
    productnames = Listing.objects.get(id=listingid)
    productnames = productnames.productnames

    descriptions = Listing.objects.get(id=listingid)
    descriptions = descriptions.descriptions
    
    images = Listing.objects.get(id=listingid)
    images = images.images

    patrimonio = Listing.objects.get(id=listingid)
    patrimonio = patrimonio.patrimonio

    idp = Listing.objects.get(id=listingid)
    idp = idp.idp
        
    bidform = BiddingForm(request.POST or None)
    if request.user.username:
        bid = float(request.POST.get("bidprice"))
        if bid > current:
            listing = Listing.objects.get(id=listingid)
            listing.startingbids = bid
            listing.save()
            try:
                if Bidding.objects.filter(id=listingid):
                    bidrow = Bidding.objects.filter(id=listingid)
                    bidrow.delete()
                    fs.time = now
                fs = bidform.save(commit=False)
                fs.bidder = request.user.email
                fs.listingid = listingid
                fs.productnames = productnames
                fs.descriptions = descriptions
                fs.startingbids = current
                fs.images = images
                fs.patrimonio = patrimonio
                fs.idp = idp
                fs.save()
                
                # construa a mensagem de e-mail para o licitante
                RECIPIENT = fs.bidder
                SUBJECT = f'Você deu um lance para o produto {listing.productnames}!'
                BODY_TEXT = f'Você deu um lance para o {listing.productnames}. \nNo valor de R$ {fs.bidprice} \nPatrimônio: {listing.patrimonio} | N°série: {listing.idp} \n\n\nAgora é só acompanhar e aguardar a contagem regressiva! \n\nBoa sorte! \n\n\n\n\n\n'
                BODY_HTML = f'Você deu um lance para o <strong>{listing.productnames}</strong>. <br>No valor de <strong>R$ {fs.bidprice}</strong> <strong><br>Patrimônio: {listing.patrimonio} </strong> | <strong>N°série: {listing.idp} </strong> <br><br><br>Agora é só acompanhar e aguardar a contagem regressiva! <br><br>Boa sorte!<br><br><br><br><br>'
            
                # Chame a função send_email para enviar o e-mail
                send_email([RECIPIENT], SUBJECT, BODY_TEXT, BODY_HTML)

                # Obtenha o último lance anterior
                previous_bid = Bidding.objects.filter(listingid=listingid).exclude(bidder=fs.bidder).order_by('-time').first()
                if previous_bid:
                    previous_bidder_email = previous_bid.bidder

                # construa a mensagem de e-mail para o licitante anterior      
                RECIPIENT = previous_bidder_email
                SUBJECT = f'Alguém cobriu seu lance para {listing.productnames}'
                BODY_TEXT = f'Alguém cobriu seu lance paro o {listing.productnames}, Patrimônio: {listing.patrimonio} | N°série: {listing.idp}. \nNovo lance: R$ {fs.bidprice}. \n\nFique de olho!🕵️🕵️🕵️\n\n\n\n\n\n'
                BODY_HTML = f'Alguém cobriu seu lance paro o <strong> {listing.productnames}</strong>, <strong>Patrimônio: {listing.patrimonio}</strong> | <strong>N°série: {listing.idp}</strong>. <br>Novo lance: R$ {fs.bidprice}. <br><br>Fique de olho!🕵️🕵️🕵️<br><br><br><br><br>'
                # Chame a função send_email para enviar o e-mail
                send_email([RECIPIENT], SUBJECT, BODY_TEXT, BODY_HTML)

            except:
                fs = bidform.save(commit=False)
                fs.bidder = request.user.email
                fs.listingid = listingid
                fs.productnames = productnames
                fs.descriptions = descriptions
                fs.startingbids = current
                fs.images = images
                fs.patrimonio = patrimonio
                fs.idp = idp
                fs.save() 
            response = redirect('listingpage', id=listingid)
            response.set_cookie(
                'success', 'Lance efetuado com sucesso!.', max_age=1)
            return response
        else:
            response = redirect('listingpage', id=listingid)
            response.set_cookie(
                'error', 'Você deve fornecer um valor maior que o preço atual', max_age=1)
            return response
    else:
        return redirect('index')


@login_required
def closebid(request, listingid):
    if request.user.username:
        try:
            listing = Listing.objects.get(id=listingid)
        except:
            return redirect('index')
        closebid = Closebid()
        name = listing.productnames
        closebid.lister = listing.lister
        closebid.listingid = listingid
        closebid.productnames = listing.productnames
        closebid.images = listing.images
        closebid.images2 = listing.images2
        closebid.images3 = listing.images3
        closebid.category = listing.category
        closebid.patrimonio = listing.patrimonio
        closebid.idp = listing.idp
        try:
            bid = Bidding.objects.get(
            listingid=listingid, bidprice=listing.startingbids)
            closebid.bidder = bid.bidder
            closebid.finalbid = bid.bidprice
            closebid.save()
            if closebid.bidder != closebid.lister:
                
                # construa a mensagem de e-mail
                RECIPIENT = bid.bidder
                SUBJECT = f'Você ganhou o leilão para o {listing.productnames}!'
                BODY_TEXT = f'Parabéns! Você ganhou o leilão para o {listing.productnames}. | Patrimônio: {closebid.patrimonio} | N°série: {listing.idp}, por R$ {closebid.finalbid}.\n\n Para darmos andamento na sua aquisição, faremos o contrato de Compra e Venda e Recibo de Entrega. Para isso, pedimos que envie os dados a seguir: \n\n- Nome Completo:\n\n- Nº RG:\n\n- Nº CPF: \n\n- Nacionalidade: \n\n- Estado Civil:\n\n- Endereço: \n\n Por gentileza, envie os dados respondendo este email ou envie para ofertaslisto@soulisto.com.br. \nEntraremos em contato para orientar quanto ao pagamento e retirada. \n\n\nAguardamos você! \n\n\n\n\n' 
                BODY_HTML = f'Parabéns! Você ganhou o leilão para o <strong>{listing.productnames}</strong>. | <strong>Patrimônio: {closebid.patrimonio}</strong> | <strong>N°série: {listing.idp}</strong>, por <strong>R$ {closebid.finalbid}</strong>.<br><br> Para darmos andamento na sua aquisição, faremos o contrato de Compra e Venda e Recibo de Entrega. Para isso, pedimos que envie os dados a seguir: <br><br>- <strong>Nome Completo:</strong><br><br>- <strong>Nº RG:</strong><br><br>- <strong>Nº CPF:</strong> <br><br>- <strong>Nacionalidade:</strong> <br><br>- <strong>Estado Civil:</strong><br><br>- <strong>Endereço:</strong> <br><br> Por gentileza, envie os dados  para <strong>ofertaslisto@soulisto.com.br</strong>. <br>Entraremos em contato para orientar quanto ao pagamento e retirada. <br><br><br>Aguardamos você! <br><br><br><br><br>'
            
                # Chame a função send_email para enviar o e-mail
                send_email([RECIPIENT], SUBJECT, BODY_TEXT, BODY_HTML)
                
            # bid.delete()
        except:
            closebid.bidder = bid.bidder
            closebid.finalbid = listing.startingbids
            closebid.save()
                
            # construa a mensagem de e-mail
            RECIPIENT = bid.bidder
            SUBJECT = f'Você ganhou o leilão para o {listing.productnames}!'
            BODY_TEXT = f'Parabéns! Você ganhou o leilão para o {listing.productnames}. | Patrimônio: {closebid.patrimonio} | N°série: {listing.idp}, por R$ {closebid.finalbid}.\n\n Para darmos andamento na sua aquisição, faremos o contrato de Compra e Venda e Recibo de Entrega. Para isso, pedimos que envie os dados a seguir: \n\n- Nome Completo:\n\n- Nº RG:\n\n- Nº CPF: \n\n- Nacionalidade: \n\n- Estado Civil:\n\n- Endereço: \n\n Por gentileza, envie os dados respondendo este email ou envie para ofertaslisto@soulisto.com.br. \nEntraremos em contato para orientar quanto ao pagamento e retirada. \n\n\nAguardamos você! \n\n\n\n\n' 
            BODY_HTML = f'Parabéns! Você ganhou o leilão para o <strong>{listing.productnames}</strong>. | <strong>Patrimônio: {closebid.patrimonio}</strong> | <strong>N°série: {listing.idp}</strong>, por <strong>R$ {closebid.finalbid}</strong>.<br><br> Para darmos andamento na sua aquisição, faremos o contrato de Compra e Venda e Recibo de Entrega. Para isso, pedimos que envie os dados a seguir: <br><br>- <strong>Nome Completo:</strong><br><br>- <strong>Nº RG:</strong><br><br>- <strong>Nº CPF:</strong> <br><br>- <strong>Nacionalidade:</strong> <br><br>- <strong>Estado Civil:</strong><br><br>- <strong>Endereço:</strong> <br><br> Por gentileza, envie os dados  para <strong>ofertaslisto@soulisto.com.br</strong>. <br>Entraremos em contato para orientar quanto ao pagamento e retirada. <br><br><br>Aguardamos você! <br><br><br><br><br>'
            send_email([RECIPIENT], SUBJECT, BODY_TEXT, BODY_HTML)        
        else:
            closebid.bidder = closebid.lister
            closebid.finalbid = listing.startingbids
            closebid.save()    
            # Chame a função send_email para enviar o e-mail
            
        try:
            if Watchlist.objects.filter(listingid=listingid):
                watch = Watchlist.objects.filter(listingid=listingid)
                watch.delete()
            else:
                pass
        except:
            pass
        try:
            comment = Comment.objects.filter(listingid=listingid)
            comment.delete()
        except:
            pass
        try:
            bid = Bid.objects.filter(listingid=listingid)
            bid.delete()
        except:
            pass
        try:
            closebidlist = Closebid.objects.get(listingid=listingid)
        except:
            closebid.lister = listing.lister
            closebid.bidder = listing.lister
            closebid.listingid = listingid
            closebid.finalbid = listing.startingbids
            closebid.productnames = listing.productnames
            closebid.images = listing.images
            closebid.category = listing.category
            closebid.idp = listing.idp
            closebid.save()
            closebidlist = Closebid.objects.get(listingid=listingid)
        listing.delete()
        try:
            watch = Watchlist.objects.filter(watcher=request.user.username)
            watchcount = len(watch)
        except:
            watchcount = None
        return render(request, "auctions/winner.html", {
            "closebidlist": closebidlist,
            "name": name,
            "watchcount": watchcount
        })
    else:
        return redirect('index')


@login_required
def closed(request, listingid):
    closed = Closebid.objects.get(listingid=listingid)
    try:
        watch = Watchlist.objects.filter(watcher=request.user.username)
        watchcount = len(watch)
    except:
        watchcount = None
    return render(request, "auctions/closed.html", {
        "object": closed,
        "watchcount": watchcount
    })


@login_required
def comment(request, listingid):
    if request.method == "POST":
        comment = Comment.objects.all()
        cform = CommentForm(request.POST or None)
        if cform.is_valid():
            now = datetime.now()
            fs = cform.save(commit=False)
            fs.listingid = listingid
            fs.user = request.user.username
            fs.time = now
            fs.save()
        return redirect('listingpage', id=listingid)
    else:
        return redirect('index')


def category(request):
    category = Category.objects.all()
    closedbid = Closebid.objects.all()
    try:
        if Watchlist.objects.get(listingid=listingid):
            closed = True
        else:
            closed = False
    except:
        closed = False
    try:
        watch = Watchlist.objects.filter(watcher=request.user.username)
        watchcount = len(watch)
    except:
        watchcount = None
    return render(request, "auctions/categories.html", {
        "object": category,
        "watchcount": watchcount,
        "closed": closed,
        "closedbid": closedbid
    })


def categorylistings(request, cats):
    category_posts = Listing.objects.filter(category=cats)
    try:
        watch = Watchlist.objects.filter(watcher=request.user.username)
        watchcount = len(watch)
    except:
        watchcount = None
    return render(request, 'auctions/categorylistings.html', {
        'cats': cats,
        'category_posts': category_posts,
        'watchcount': watchcount
    })


def allclosed(request):
    closedlist = Closebid.objects.all()
    try:
        watch = Watchlist.objects.filter(watcher=request.user.username)
        watchcount = len(watch)
    except:
        watchcount = None
    return render(request, 'auctions/allclosed.html', {
        'closedlist': closedlist,
        'watchcount': watchcount
    })


def login_view(request):
    if request.method == "POST":
        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Validação de emails Listo
        with open('emails.txt', 'r') as f:
            emails_validos = f.read().splitlines()

        if email not in emails_validos:
            return render(request, "auctions/register.html", {"message": "Entre com um usuário válido."})

        # Generate a random password of length 10 with letters, digits.
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })

        # Construa os parâmetros do e-mail
        subject = 'Senha para autenticação'
        message = f'Olá {username},\n\nSua senha é: {password}\n\nPor favor, mantenha segura e não compartilhe com ninguém.\n\n Leilão Listo\n\n\n\n\n'
        from_email = 'ofertaslisto@soulisto.com.br'
        recipient_list = [email]
        html_message = f'Olá {username},<br> <br> Sua senha é: <strong>{password}</strong> <br> <br> Por favor, mantenha segura e não compartilhe com ninguém. <br> <br> Leilão Listo <br> <br> <br> <br> <br>'

        # construa a mensagem de e-mail para o licitante
        RECIPIENT = email
        SUBJECT = 'Senha para autenticação'
        BODY_TEXT = f'Olá {username},\n\nSua senha é: {password}\n\nPor favor, mantenha segura e não compartilhe com ninguém.\n\n Leilão Listo\n\n\n\n\n'
        BODY_HTML = f'Olá <strong>{username}</strong>,<br><br>Sua senha é: <strong>{password}</strong><br><br>Por favor, mantenha segura e não compartilhe com ninguém.<br><br> Ofertas Listo<br><br><br><br>' 
            
        # Chame a função send_email para enviar o e-mail
        send_email([RECIPIENT], SUBJECT, BODY_TEXT, BODY_HTML)


        return render(request, "auctions/password_reset_done.html")
    else:
        return render(request, "auctions/register.html")


def termos_e_condicoes(request):
    return render(request, "auctions/termos.html")


def closeallbids(request):
    if request.user.is_superuser:
        # Obtém todos os objetos Listing do índice
        listings = Listing.objects.all()
        for listing in listings:
            closebid = Closebid()
            closebid.lister = listing.lister
            closebid.listingid = listing.id
            closebid.productnames = listing.productnames
            closebid.images = listing.images
            closebid.images2 = listing.images2
            closebid.images3 = listing.images3
            closebid.category = listing.category
            closebid.patrimonio = listing.patrimonio
            closebid.idp = listing.idp
            try:
                bid = Bidding.objects.filter(listingid=listing.id).order_by('-bidprice')[0]
                closebid.bidder = bid.bidder
                closebid.finalbid = bid.bidprice
            except:
                closebid.bidder = listing.lister
                closebid.finalbid = listing.startingbids
            closebid.save()
            if closebid.bidder != closebid.lister:
                
                # construa a mensagem de e-mail
                RECIPIENT = bid.bidder
                SUBJECT = f'Você ganhou o leilão para o {listing.productnames}!'
                BODY_TEXT = f'Parabéns! Você ganhou o leilão para o {listing.productnames}. | Patrimônio: {closebid.patrimonio} | N°série: {listing.idp}, por R$ {closebid.finalbid}.\n\n Para darmos andamento na sua aquisição, faremos o contrato de Compra e Venda e Recibo de Entrega. Para isso, pedimos que envie os dados a seguir: \n\n- Nome Completo:\n\n- Nº RG:\n\n- Nº CPF: \n\n- Nacionalidade: \n\n- Estado Civil:\n\n- Endereço: \n\n Por gentileza, envie os dados respondendo este email ou envie para ofertaslisto@soulisto.com.br. \nEntraremos em contato para orientar quanto ao pagamento e retirada. \n\n\nAguardamos você! \n\n\n\n\n' 
                BODY_HTML = f'Parabéns! Você ganhou o leilão para o <strong>{listing.productnames}</strong>. | <strong>Patrimônio: {closebid.patrimonio}</strong> | <strong>N°série: {listing.idp}</strong>, por <strong>R$ {closebid.finalbid}</strong>.<br><br> Para darmos andamento na sua aquisição, faremos o contrato de Compra e Venda e Recibo de Entrega. Para isso, pedimos que envie os dados a seguir: <br><br>- <strong>Nome Completo:</strong><br><br>- <strong>Nº RG:</strong><br><br>- <strong>Nº CPF:</strong> <br><br>- <strong>Nacionalidade:</strong> <br><br>- <strong>Estado Civil:</strong><br><br>- <strong>Endereço:</strong> <br><br> Por gentileza, envie os dados  para <strong>ofertaslisto@soulisto.com.br</strong>. <br>Entraremos em contato para orientar quanto ao pagamento e retirada. <br><br><br>Aguardamos você! <br><br><br><br><br>' 
            
                # Chame a função send_email para enviar o e-mail
                send_email([RECIPIENT], SUBJECT, BODY_TEXT, BODY_HTML)
                
            try:
                if Watchlist.objects.filter(listingid=listing.id):
                    watch = Watchlist.objects.filter(listingid=listing.id)
                    watch.delete()
            except:
                pass
            try:
                comment = Comment.objects.filter(listingid=listing.id)
                comment.delete()
            except:
                pass
            try:
                bid = Bid.objects.filter(listingid=listing.id)
                bid.delete()
            except:
                pass
            try:
                closebidlist = Closebid.objects.get(listingid=listing.id)
            except:
                closebid.lister = listing.lister
                closebid.bidder = listing.lister
                closebid.listingid = listing.id
                closebid.finalbid = listing.startingbids
                closebid.productnames = listing.productnames
                closebid.images = listing.images
                closebid.category = listing.category
                closebid.patrimonio = listing.patrimonio
                closebid.idp = listing.idp
                closebid.save()
                closebidlist = Closebid.objects.get(listingid=listing.id)
            listing.delete()
        
    return render(request, 'auctions/categories.html')


def password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(request=request)
            return render(request, 'auctions/password_reset_done.html')
    else:
        form = PasswordResetForm()
    return render(request, 'auctions/password_reset_form.html', {'form': forms})


def password_reset_done(request):
    return render(request, 'auctions/password_reset_done.html')


from django.http import JsonResponse

@login_required
def editar_produto(request, id):
    # busca o objeto Listing a ser editado
    listing = get_object_or_404(Listing, id=id)

    # verifica se o usuário é o mesmo que criou o produto
    #if request.user.email != listing.lister:
        # usuário não tem permissão para editar este produto
        #return redirect('listingpage', id=id)

    if request.method == 'POST':
        # cria uma instância do ListingForm, preenchido com os dados do POST
        form = ListingForm(request.POST, instance=listing)

        if form.is_valid():
            # salva o objeto Listing atualizado no banco de dados
            form.save()
            # redireciona o usuário para a página de detalhes do produto atualizado
            return redirect('listingpage', id=id)

    else:
        # exibe o formulário de edição de produto preenchido com os dados atuais do produto
        form = ListingForm(instance=listing)

    context = {'form': form, 'listing': listing}
    return render(request, 'auctions/editar_produto.html', context)




def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Sua senha foi alterada com sucesso!')
            return render(request, 'auctions/index.html')
        else:
            messages.error(request, 'Por favor, corrija o(s) erro(s) abaixo.')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'auctions/change_password.html', {'form': form})



def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            user.set_password(new_password)
            user.save()
            
            RECIPIENT = email
            SUBJECT = 'Nova senha para o aplicativo'
            BODY_TEXT = 'Sua nova senha é: ' + new_password
            BODY_HTML = 'Sua nova senha é: <strong>' + new_password + '</strong> <br> <br> <br>'
            
            # Chame a função send_email para enviar o e-mail
            send_email([RECIPIENT], SUBJECT, BODY_TEXT, BODY_HTML)          

            return redirect('password_reset_done')
        except User.DoesNotExist:
            error_message = 'Endereço de e-mail não cadastrado.'
            return render(request, 'auctions/password_reset.html', {'error_message': error_message})
    return render(request, 'auctions/password_reset.html')


def password_reset_done(request):
    return render(request, 'auctions/password_reset_done.html')





