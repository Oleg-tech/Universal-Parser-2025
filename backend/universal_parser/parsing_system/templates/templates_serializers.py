from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import Template

User = get_user_model()


class TemplateSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Template
        fields = [
            'id',
            'name',
            'hashed_name',
            'base_hashed_name',
            'webresource_url',
            'number_of_scrapes',
            'is_automated',
            'last_scrape',
            'delay_between_scrapes',
            'user'
        ]
        read_only_fields = ['id', 'user']

    def validate_webresource_url(self, value):
        """
        Validate that the URL is properly formatted
        """
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value

    def validate_delay_between_scrapes(self, value):
        """
        Ensure delay is not negative
        """
        if value < 0:
            raise serializers.ValidationError("Delay between scrapes cannot be negative")
        return value


class TemplateCreateSerializer(serializers.ModelSerializer):
    """
    Separate serializer for creation to handle different validation if needed
    """
    name = serializers.CharField(max_length=150, write_only=True)
    hashed_name = serializers.CharField(read_only=True)
    base_hashed_name = serializers.CharField(read_only=True)

    class Meta:
        model = Template
        fields = [
            'name',
            'hashed_name',
            'base_hashed_name',
            'webresource_url',
            'is_automated',
            'delay_between_scrapes'
        ]

    def create(self, validated_data):
        import hashlib
        import uuid
        from django.utils import timezone

        # Extract the name field
        web_resource_url = validated_data.pop('webresource_url')

        # Create base hash from name
        base_hash = hashlib.md5(web_resource_url.encode('utf-8')).hexdigest()

        # Create unique hashed_name by adding timestamp and UUID
        timestamp = str(int(timezone.now().timestamp()))
        unique_suffix = str(uuid.uuid4())[:8]
        unique_string = f"{web_resource_url}_{timestamp}_{unique_suffix}"
        hashed_name = hashlib.sha256(unique_string.encode('utf-8')).hexdigest()[:30]

        # Ensure uniqueness (in case of collision)
        counter = 1
        original_hashed_name = hashed_name
        while Template.objects.filter(hashed_name=hashed_name).exists():
            hashed_name = f"{original_hashed_name}_{counter}"
            counter += 1

        # Set the hashed values
        validated_data['hashed_name'] = hashed_name
        validated_data['base_hashed_name'] = base_hash

        return super().create(validated_data)
