from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# =============================
# 🔹 UTILISATEUR (Étudiant / Vendeur)
# =============================
class User(AbstractUser):
    # Django fournit déjà username, password, email
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    student_document = models.FileField(upload_to="documents/", blank=True, null=True)


    # Pour différencier les rôles plus tard (étudiant / admin / autre)
    ROLE_CHOICES = [
        ('STUDENT', 'Étudiant'),
        ('SELLER', 'Vendeur'),
        ('ADMIN', 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT')

    def __str__(self):
        return f"{self.username} ({self.role})"




# =============================
# 🔹 MEUBLE À VENDRE OU À LOUER
# =============================
class Item(models.Model):
    TYPE_CHOICES = [
        ('SELL', 'Vente'),
        ('RENT', 'Location'),
    ]


    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    item_type = models.CharField(max_length=4, choices=TYPE_CHOICES)

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="items", null=True, blank=True)

    city = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)

    image = models.ImageField(upload_to="items/", blank=True, null=True)
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_item_type_display()})"

class ItemImage(models.Model):
    item = models.ForeignKey(
        'Item',
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='items/')

    def __str__(self):
        return f"Image de {self.item.title}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Panier de {self.user.email}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return float(self.item.price) * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.item.title}"

        from django.db import models

class Payment(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'En attente'),
        ('COMPLETED', 'Complété'),
        ('FAILED', 'Échoué'),
        ('CANCELLED', 'Annulé'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    cart = models.ForeignKey(
        'Cart',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )

    paypal_order_id = models.CharField(
        max_length=255,
        help_text="ID de commande retourné par PayPal",
        unique=True
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='PENDING'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    payer_email = models.EmailField(blank=True, null=True)
    payer_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Paiement {self.paypal_order_id} - {self.status}"

    class Meta:
        ordering = ['-created_at']
