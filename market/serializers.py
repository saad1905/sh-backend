from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User,Item,ItemImage,Cart,CartItem,Payment


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # 🧩 On inclut tous les champs du modèle
        fields = '__all__'



class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    student_document = serializers.FileField(required=False, allow_null=True)  # 🆕 ajouté

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'password',
            'city',
            'phone',
            'profile_picture',
            'student_document',  # 🆕 ajouté
        ]

    def create(self, validated_data):
        profile_picture = validated_data.pop('profile_picture', None)
        student_document = validated_data.pop('student_document', None)  # 🆕 ajouté

        # Générer automatiquement un username unique basé sur l'email
        email = validated_data.get('email')
        base_username = email.split('@')[0] if email else 'user'
        counter = 1
        username = base_username
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            email=email,
            city=validated_data.get('city', ''),
            phone=validated_data.get('phone', '')
        )

        if profile_picture:
            user.profile_picture = profile_picture
        if student_document:
            user.student_document = student_document  # 🆕 ajouté
        user.save()

        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        request = self.context.get('request')  # 🔹 Permet d’envoyer le contexte depuis la vue
        email = data.get("email")
        password = data.get("password")

        # Vérifier que l'utilisateur existe
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username  # Django authentifie toujours avec "username"
        except User.DoesNotExist:
            raise serializers.ValidationError("Adresse email ou mot de passe incorrect.")

        # 🔹 Authentification liée à la requête (important pour les sessions)
        user = authenticate(request=request, username=username, password=password)
        if not user:
            raise serializers.ValidationError("Adresse email ou mot de passe incorrect.")

        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé.")

        return user
class ItemSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField(read_only=True)
    images = serializers.SerializerMethodField(read_only=True)  # ✅ Ajout du champ images

    class Meta:
        model = Item
        fields = [
            'id', 'owner_name', 'title', 'description', 'price', 'item_type',
            'city', 'address', 'contact_phone', 'is_available',
            'created_at', 'updated_at', 'owner', 'images'  # ✅ on ajoute images ici
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']

    def get_owner_name(self, obj):
        return f"{obj.owner.first_name} {obj.owner.last_name}" if obj.owner else None

    def get_images(self, obj):
        """Retourne toutes les images associées à l’item."""
        request = self.context.get('request')
        if hasattr(obj, "images"):  # related_name="images" dans ItemImage
            return [
                {"id": img.id, "image": request.build_absolute_uri(img.image.url)}
                for img in obj.images.all() if img.image
            ]
        return []


class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ['id', 'image']  

class RentItemSerializer(serializers.ModelSerializer):
    images = ItemImageSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = [
            'id', 'title', 'description', 'price', 'city',
            'address', 'contact_phone', 'item_type',
            'is_available', 'created_at', 'updated_at', 'images'
        ]
        extra_kwargs = {
            'item_type': {'required': False}  # ✅ Rendre non obligatoire
        }

    def create(self, validated_data):
        validated_data['item_type'] = 'RENT'
        return super().create(validated_data)
    images = ItemImageSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = [
            'id', 'title', 'description', 'price', 'city',
            'address', 'contact_phone', 'item_type',
            'is_available', 'created_at', 'updated_at',
            'images'
        ]

    # ✅ Forcer automatiquement l’item_type à "SELL"
    def create(self, validated_data):
        validated_data['item_type'] = 'RENT'
        return super().create(validated_data)

class SellItemSerializer(serializers.ModelSerializer):
    images = ItemImageSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = [
            'id', 'title', 'description', 'price', 'city',
            'address', 'contact_phone', 'item_type',
            'is_available', 'created_at', 'updated_at', 'images'
        ]
        extra_kwargs = {
            'item_type': {'required': False}  # ✅ Rendre non obligatoire
        }

    def create(self, validated_data):
        validated_data['item_type'] = 'SELL'
        return super().create(validated_data)
    images = ItemImageSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = [
            'id', 'title', 'description', 'price', 'city',
            'address', 'contact_phone', 'item_type',
            'is_available', 'created_at', 'updated_at',
            'images'
        ]

    # ✅ Forcer automatiquement l’item_type à "SELL"
    def create(self, validated_data):
        validated_data['item_type'] = 'SELL'
        return super().create(validated_data)

class CartItemSerializer(serializers.ModelSerializer):
    item = SellItemSerializer(read_only=True)  # ✅ Utilise le même serializer que /sell-items/
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=CartItem._meta.get_field('item').remote_field.model.objects.all(),
        source='item',
        write_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'item', 'item_id', 'quantity', 'total_price']
        read_only_fields = ['total_price']
    item = ItemSerializer(read_only=True)
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=CartItem._meta.get_field('item').remote_field.model.objects.all(),
        source='item',
        write_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'item', 'item_id', 'quantity', 'total_price']
        read_only_fields = ['total_price']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'created_at']
        read_only_fields = ['user', 'created_at']

class PaymentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    cart_id = serializers.IntegerField(source='cart.id', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'paypal_order_id',
            'user',
            'user_email',
            'cart',
            'cart_id',
            'amount',
            'currency',
            'status',
            'payer_email',
            'payer_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at', 'user_email', 'payer_email', 'payer_id']

    def create(self, validated_data):
        """
        Crée une instance Payment lors de la création d'une commande PayPal.
        """
        payment = Payment.objects.create(**validated_data)
        return payment