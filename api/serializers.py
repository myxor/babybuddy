# -*- coding: utf-8 -*-
from copy import deepcopy
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.contrib.auth.models import User
from django.utils import timezone

from taggit.serializers import TagListSerializerField

from core import models


class CoreModelSerializer(serializers.HyperlinkedModelSerializer):
    """
    Provide the child link (used by most core models) and run model clean()
    methods during POST operations.
    """

    child = serializers.PrimaryKeyRelatedField(queryset=models.Child.objects.all())

    def validate(self, attrs):
        # Ensure that all instance data is available for partial updates to
        # support clean methods that compare multiple fields.
        if self.partial:
            new_instance = deepcopy(self.instance)
            for attr, value in attrs.items():
                setattr(new_instance, attr, value)
        else:
            new_instance = self.Meta.model(**attrs)
        new_instance.clean()
        return attrs


class CoreModelWithDurationSerializer(CoreModelSerializer):
    """
    Specific serializer base for models with a "start" and "end" field.
    """

    child = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        allow_empty=True,
        queryset=models.Child.objects.all(),
        required=False,
    )

    class Meta:
        abstract = True
        extra_kwargs = {
            "start": {"required": False},
            "end": {"required": False},
        }

    def validate(self, attrs):
        # Check for a special "timer" data argument that can be used in place
        # of "start" and "end" fields as well as "child" if it is set on the
        # Timer entry.
        timer = None
        if "timer" in self.initial_data:
            try:
                timer = models.Timer.objects.get(pk=self.initial_data["timer"])
            except models.Timer.DoesNotExist:
                raise ValidationError({"timer": ["Timer does not exist."]})
            if timer.end:
                end = timer.end
            else:
                end = timezone.now()
            if timer.child:
                attrs["child"] = timer.child

            # Overwrites values provided directly!
            attrs["start"] = timer.start
            attrs["end"] = end

        # The "child", "start", and "end" field should all be set at this
        # point. If one is not, model validation will fail because they are
        # required fields at the model level.
        if not self.partial:
            errors = {}
            for field in ["child", "start", "end"]:
                if field not in attrs or not attrs[field]:
                    errors[field] = "This field is required."
            if len(errors) > 0:
                raise ValidationError(errors)

        attrs = super().validate(attrs)

        # Only actually stop the timer if all validation passed.
        if timer:
            timer.stop(attrs["end"])

        return attrs


class TaggableSerializer(serializers.HyperlinkedModelSerializer):
    tags = TagListSerializerField(required=False)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")


class PumpingSerializer(CoreModelSerializer):
    class Meta:
        model = models.Pumping
        fields = ("id", "child", "amount", "time", "notes")


class ChildSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Child
        fields = ("id", "first_name", "last_name", "birth_date", "slug", "picture")
        lookup_field = "slug"


class DiaperChangeSerializer(CoreModelSerializer, TaggableSerializer):
    class Meta:
        model = models.DiaperChange
        fields = (
            "id",
            "child",
            "time",
            "wet",
            "solid",
            "color",
            "amount",
            "notes",
            "tags",
        )


class FeedingSerializer(CoreModelWithDurationSerializer, TaggableSerializer):
    class Meta(CoreModelWithDurationSerializer.Meta):
        model = models.Feeding
        fields = (
            "id",
            "child",
            "start",
            "end",
            "duration",
            "type",
            "method",
            "amount",
            "notes",
            "tags",
        )


class NoteSerializer(CoreModelSerializer, TaggableSerializer):
    class Meta:
        model = models.Note
        fields = ("id", "child", "note", "time", "tags")


class SleepSerializer(CoreModelWithDurationSerializer, TaggableSerializer):
    class Meta(CoreModelWithDurationSerializer.Meta):
        model = models.Sleep
        fields = ("id", "child", "start", "end", "duration", "nap", "notes", "tags")


class TemperatureSerializer(CoreModelSerializer, TaggableSerializer):
    class Meta:
        model = models.Temperature
        fields = ("id", "child", "temperature", "time", "notes", "tags")


class TimerSerializer(CoreModelSerializer):
    child = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        allow_empty=True,
        queryset=models.Child.objects.all(),
        required=False,
    )
    user = serializers.PrimaryKeyRelatedField(
        allow_null=True, allow_empty=True, queryset=User.objects.all(), required=False
    )

    class Meta:
        model = models.Timer
        fields = ("id", "child", "name", "start", "end", "duration", "active", "user")

    def validate(self, attrs):
        attrs = super(TimerSerializer, self).validate(attrs)

        # Set user to current user if no value is provided.
        if "user" not in attrs or attrs["user"] is None:
            attrs["user"] = self.context["request"].user

        return attrs


class TummyTimeSerializer(CoreModelWithDurationSerializer, TaggableSerializer):
    class Meta(CoreModelWithDurationSerializer.Meta):
        model = models.TummyTime
        fields = ("id", "child", "start", "end", "duration", "milestone", "tags")


class WeightSerializer(CoreModelSerializer, TaggableSerializer):
    class Meta:
        model = models.Weight
        fields = ("id", "child", "weight", "date", "notes", "tags")


class HeightSerializer(CoreModelSerializer, TaggableSerializer):
    class Meta:
        model = models.Height
        fields = ("id", "child", "height", "date", "notes", "tags")


class HeadCircumferenceSerializer(CoreModelSerializer, TaggableSerializer):
    class Meta:
        model = models.HeadCircumference
        fields = ("id", "child", "head_circumference", "date", "notes", "tags")


class BMISerializer(CoreModelSerializer, TaggableSerializer):
    class Meta:
        model = models.BMI
        fields = ("id", "child", "bmi", "date", "notes", "tags")


class TagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Tag
        fields = ("slug", "name", "color", "last_used")
        extra_kwargs = {
            "slug": {"required": False, "read_only": True},
            "color": {"required": False},
            "last_used": {"required": False, "read_only": True},
        }
