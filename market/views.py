from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from .models import User,Item,ItemImage,Cart,CartItem,Payment
from .serializers import RegisterSerializer, LoginSerializer,UserListSerializer,ItemSerializer,SellItemSerializer,ItemImageSerializer,CartSerializer,CartItemSerializer,RentItemSerializer,PaymentSerializer
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import stripe



# @method_decorator(csrf_exempt, name='dispatch')
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les utilisateurs :
    - GET /users/ → liste des utilisateurs (admin)
    - GET /users/{id}/ → détail
    - POST /users/ → création manuelle
    - POST /users/register/ → inscription
    - POST /users/login/ → connexion
    - POST /users/logout/ → déconnexion
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer  # par défaut
    permission_classes = [AllowAny]
    def get_serializer_class(self):
        """
        🔹 Utiliser un serializer différent selon l’action
        """
        if self.action == 'list' or self.action == 'retrieve':
            return UserListSerializer
        elif self.action == 'register':
            return RegisterSerializer
        return super().get_serializer_class()


    # 🔹 REGISTER
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": f"Utilisateur {user.username} créé avec succès !",
                "username": user.username,
                "email": user.email,
                "profile_picture": request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
                "student_document": request.build_absolute_uri(user.student_document.url) if user.student_document else None,  # 🆕
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    # 🔹 LOGIN
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        login(request, user)
        return Response({
            "message": f"Bienvenue {user.first_name} {user.last_name} ! Vous êtes connecté.",
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_picture": request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
            "student_document": request.build_absolute_uri(user.student_document.url) if user.student_document else None,  # ✅ ajouté ici

        }, status=status.HTTP_200_OK)


    # 🔹 LOGOUT
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        logout(request)
        return Response({"message": "Déconnexion réussie."}, status=status.HTTP_200_OK)

    # 🔹 PROFILE
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def profile(self, request):
        user = request.user

        # 🧠 Si pas connecté, renvoyer un message par défaut (évite l'erreur 500)
        if not user.is_authenticated:
            return Response({
                "message": "Aucun utilisateur connecté.",
                "username": None,
                "first_name": None,
                "last_name": None,
                "email": None,
                "city": None,
                "phone": None,
                "profile_picture": None,
            })

        # ✅ Si connecté, afficher les infos
        return Response({
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "city": user.city,
            "phone": user.phone,
            "profile_picture": request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
        })


@api_view(['GET'])
@ensure_csrf_cookie
def get_csrf_token(request):
    return Response({"detail": "CSRF cookie set"})

class RentItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.filter(item_type='RENT')
    serializer_class = RentItemSerializer
    permission_classes = [AllowAny]


    def perform_create(self, serializer):
        email = self.request.data.get("owner_email")
        user = User.objects.filter(email=email).first()

        # ✅ On crée l’item avec le bon owner et type SELL
        item = serializer.save(owner=user, item_type='RENT')

        # ✅ Gérer les images multiples
        images = self.request.FILES.getlist('images')
        for img in images:
            ItemImage.objects.create(item=item, image=img)

class SellItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.filter(item_type='SELL')
    serializer_class = SellItemSerializer
    permission_classes = [AllowAny]


    def perform_create(self, serializer):
        email = self.request.data.get("owner_email")
        user = User.objects.filter(email=email).first()

        # ✅ On crée l’item avec le bon owner et type SELL
        item = serializer.save(owner=user, item_type='SELL')

        # ✅ Gérer les images multiples
        images = self.request.FILES.getlist('images')
        for img in images:
            ItemImage.objects.create(item=item, image=img)

class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        email = self.request.query_params.get("email")
        if email:
            user = User.objects.filter(email=email).first()
            if user:
                return Cart.objects.filter(user=user)
        return Cart.objects.none()

    def create(self, request, *args, **kwargs):
        """🛒 Crée le panier si non existant"""
        email = request.data.get("email")
        user = User.objects.filter(email=email).first()

        if not user:
            return Response({"error": "Utilisateur introuvable."}, status=status.HTTP_400_BAD_REQUEST)

        cart, created = Cart.objects.get_or_create(user=user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='add')
    def add_to_cart(self, request):
        """➕ Ajouter un article au panier"""
        email = request.data.get("email")
        item_id = request.data.get("item_id")
        quantity = int(request.data.get("quantity", 1))

        user = User.objects.filter(email=email).first()
        item = Item.objects.filter(id=item_id).first()

        if not user or not item:
            return Response({"error": "Utilisateur ou article introuvable."}, status=status.HTTP_400_BAD_REQUEST)

        cart, _ = Cart.objects.get_or_create(user=user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
        if not created:
            cart_item.quantity += quantity
        cart_item.save()

        return Response({"message": "✅ Article ajouté au panier."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='remove')
    def remove_from_cart(self, request):
        """🗑️ Supprimer un article du panier"""
        email = request.data.get("email")
        item_id = request.data.get("item_id")

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "Utilisateur introuvable."}, status=status.HTTP_404_NOT_FOUND)

        cart = Cart.objects.filter(user=user).first()
        if not cart:
            return Response({"error": "Panier introuvable."}, status=status.HTTP_404_NOT_FOUND)

        deleted, _ = CartItem.objects.filter(cart=cart, item_id=item_id).delete()
        if deleted:
            return Response({"message": "🗑️ Article supprimé du panier."})
        return Response({"error": "Article non trouvé."}, status=status.HTTP_404_NOT_FOUND)

import requests
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Payment, Cart, User
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [AllowAny]

    # ===================================
    # 🔹 Conversion MAD → USD
    # ===================================
    def convert_mad_to_usd(self, amount_mad):
        """
        Convertit MAD en USD via une API gratuite.
        Fallback vers un taux fixe si l’API ne répond pas.
        """
        try:
            response = requests.get("https://api.exchangerate-api.com/v4/latest/MAD")
            if response.status_code == 200:
                data = response.json()
                usd_rate = data["rates"].get("USD", 0.10)  # sécurité
                return round(float(amount_mad) * usd_rate, 2)
        except Exception:
            pass  # en cas d'erreur réseau
        # taux de secours : 1 MAD ≈ 0.10 USD
        return round(float(amount_mad) * 0.10, 2)

    # ===================================
    # 🔐 Token PayPal
    # ===================================
    def get_paypal_access_token(self):
        auth_response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET),
            data={"grant_type": "client_credentials"},
        )
        auth_response.raise_for_status()
        return auth_response.json()["access_token"]

    # ===================================
    # 🧾 Créer une commande PayPal
    # ===================================
    @action(detail=False, methods=["post"], url_path="create-order")
    def create_order(self, request):
        email = request.data.get("email")
        amount_mad = request.data.get("amount")

        if not amount_mad:
            return Response({"error": "Montant manquant."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "Utilisateur introuvable."}, status=status.HTTP_400_BAD_REQUEST)

        cart = Cart.objects.filter(user=user).first()

        # 💱 Conversion MAD → USD
        amount_usd = self.convert_mad_to_usd(amount_mad)

        access_token = self.get_paypal_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "USD",
                        "value": str(amount_usd)
                    },
                    "description": f"Achat meubles étudiant ({amount_mad} MAD ≈ {amount_usd} USD)"
                }
            ],
            "application_context": {
                "return_url": "http://localhost:3000/payment-success",
                "cancel_url": "http://localhost:3000/payment-cancel"
            }
        }

        response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders",
            json=payload,
            headers=headers
        )

        if response.status_code != 201:
            return Response(response.json(), status=response.status_code)

        data = response.json()
        order_id = data["id"]

        # 💾 Sauvegarder la transaction
        Payment.objects.create(
            user=user,
            cart=cart,
            paypal_order_id=order_id,
            payment_method="paypal",   # ✅ OBLIGATOIRE
            amount=amount_mad,
            currency="MAD",
            status="PENDING"
        )


        approval_url = next(
            (link["href"] for link in data["links"] if link["rel"] == "approve"),
            None
        )

        return Response({
            "order_id": order_id,
            "approval_url": approval_url,
            "amount_mad": amount_mad,
            "amount_usd": amount_usd
        }, status=status.HTTP_201_CREATED)

    # ===================================
    # 💰 Capture de paiement
    # ===================================
    @action(detail=False, methods=["post"], url_path="capture-order")
    def capture_order(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"error": "order_id manquant."}, status=status.HTTP_400_BAD_REQUEST)

        access_token = self.get_paypal_access_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        response = requests.post(
            f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
            headers=headers
        )

        data = response.json()
        if response.status_code not in [200, 201]:
            return Response(data, status=response.status_code)

        payment = Payment.objects.filter(paypal_order_id=order_id).first()
        if payment:
            payment.status = "COMPLETED"
            payment.payer_email = data.get("payer", {}).get("email_address")
            payment.payer_id = data.get("payer", {}).get("payer_id")
            payment.save()

        return Response({
            "message": "Paiement capturé avec succès.",
            "payment": PaymentSerializer(payment).data if payment else None
        })

    # ===================================
    # 💳 Créer un paiement Stripe
    # ===================================
    @action(
        detail=False,
        methods=["post"],
        url_path="create-payment-stripe",
        permission_classes=[AllowAny]
    )
    def create_payment_stripe(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        email = request.data.get("email")
        amount_mad = request.data.get("amount")

        if not email or not amount_mad:
            return Response(
                {"error": "email ou amount manquant."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"error": "Utilisateur introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        cart = Cart.objects.filter(user=user).first()

        amount_usd = self.convert_mad_to_usd(amount_mad)

        intent = stripe.PaymentIntent.create(
            amount=int(float(amount_usd) * 100),
            currency="usd",
            payment_method_types=["card"],
            description=f"Achat meubles étudiant ({amount_mad} MAD)",
        )

        payment = Payment.objects.create(
            user=user,
            cart=cart,
            stripe_payment_intent_id=intent.id,
            payment_method="stripe",
            amount=amount_mad,
            currency="MAD",
            status="PENDING"
        )

        return Response(
            {
                "client_secret": intent.client_secret,
                "payment_id": payment.id
            },
            status=status.HTTP_201_CREATED
        )

    # ===================================
    # ✅ Confirmer paiement Stripe
    # ===================================
    @action(
        detail=False,
        methods=["post"],
        url_path="confirm-stripe-payment",
        permission_classes=[AllowAny]
    )
    def confirm_stripe_payment(self, request):
        payment_intent_id = request.data.get("payment_intent_id")

        payment = Payment.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).first()

        if not payment:
            return Response({"error": "Paiement introuvable"}, status=404)

        payment.status = "COMPLETED"
        payment.save()

        return Response({"message": "Paiement Stripe confirmé"})
