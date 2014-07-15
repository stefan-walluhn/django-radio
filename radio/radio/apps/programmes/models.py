import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _


SPANISH = "ES"
GALICIAN = "GA"
LANGUAGES = ((SPANISH, _("Spanish")),
    (GALICIAN, _("Galician")))


PRESENTER = 'PR'
INFORMER = 'IN'
CONTRIBUTOR = 'CO'
NOT_SPECIFIED = 'NO'

ROLES = ((NOT_SPECIFIED, _("Not specified")),
    (PRESENTER, _("Presenter")),
    (INFORMER, _("Informer")),
    (CONTRIBUTOR, _("Contributor")))


class Programme(models.Model):
    CATEGORY_CHOICES = (
        ('Arts', _('Arts')),
        ('Business', _('Business')),
        ('Comedy', _('Comedy')),
        ('Education', _('Education')),
        ('Games & Hobbies', _('Games & Hobbies')),
        ('Government & Organizations', _('Government & Organizations')),
        ('Health', _('Health')),
        ('Kids & Family', _('Kids & Family')),
        ('Music', _('Music')),
        ('News & Politics', _('News & Politics')),
        ('Religion & Spirituality', _('Religion & Spirituality')),
        ('Science & Medicine', _('Science & Medicine')),
        ('Society & Culture', _('Society & Culture')),
        ('Sports & Recreation', _('Sports & Recreation')),
        ('Technology', _('Technology')),
        ('TV & Film', _('TV & Film')),
    )

    name = models.CharField(max_length=100, unique=True, verbose_name=_("name"), help_text=_("Please DON'T change this value. It's used to build URL's."))
    start_date = models.DateField(verbose_name=_('start date'))
    end_date = models.DateField(blank=True, null=True, verbose_name=_('end date'), help_text=_("This field can be null."))
    announcers = models.ManyToManyField(User, blank=True, null=True, through='Role', verbose_name=_("announcers"))
    synopsis = models.TextField(blank=True, verbose_name=_("synopsis"))
    photo = models.ImageField(upload_to='photos/', default='/static/radio/images/default-programme-photo.jpg', verbose_name=_("photo"))
    language = models.CharField(verbose_name=_("language"), choices=LANGUAGES, max_length=2, default=SPANISH)
    current_season = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    category = models.CharField(blank=True, null=True, max_length=50, choices=CATEGORY_CHOICES)
    slug = models.SlugField(max_length=100, unique=True)
    _runtime = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    @property
    def runtime(self):
        return datetime.timedelta(minutes=self._runtime)

    @runtime.setter
    def runtime(self, value):
        self._runtime = value

    def clean(self):
        if self._runtime <= 0:
            raise ValidationError(_('Duration must be greater than 0.'))
        if self.end_date is not None and self.start_date > self.end_date:
            raise ValidationError(_('end date must be greater than or equal to start date.'))

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Programme, self).save(*args, **kwargs)


    @classmethod
    def actives(cls, start_date, end_date=None):
        programme_list = cls.objects.filter(end_date__isnull=True).order_by('-start_date') | cls.objects.filter(end_date__gte=start_date).order_by('-start_date')
        if end_date:
            programme_list = programme_list.filter(start_date__lte=end_date)
        return programme_list

    class Meta:
        verbose_name = _('programme')
        verbose_name_plural = _('programmes')
        ordering = ['name']
        permissions = (
            ("change_his_programme", "Can change some information"),
        )

    def get_absolute_url(self):
        return reverse('programmes:detail', args=[self.slug])

    def __unicode__(self):
        return self.name


class Episode(models.Model):
    title = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("title"))
    programme = models.ForeignKey(Programme, verbose_name=_("programme"))
    summary = models.TextField(blank=True, verbose_name=_("summary"))
    issue_date = models.DateTimeField(db_index=True, unique=True, verbose_name=_('issue date'))
    season = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_("season"))
    number_in_season = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_("No. in season"))
    # slug = models.SlugField(max_length=100)

    @classmethod
    def create_episode(cls, date, programme):
        last_episode = Episode.get_last_episode(programme)
        if last_episode:
            season = last_episode.season
            number_in_season = last_episode.number_in_season + 1
        else:
            season = programme.current_season
            number_in_season = 1
        episode = Episode(programme=programme, issue_date=date, season=season, number_in_season=number_in_season)
        episode.save()
        # participants added in post_save signal
        return episode

    @classmethod
    def next_episodes(cls, programme, hour, after=None):
        # TODO: improve query
        if after == None:
            after = datetime.datetime.now()
        episodes = Episode.objects.filter(programme=programme, issue_date__gte=after).order_by('issue_date')
        next_episodes = []
        for episode in episodes:
            if episode.issue_date.time() == hour:
                next_episodes.append(episode)
        return next_episodes

    @classmethod
    def get_last_episode(cls, programme):
        return cls.objects.filter(programme=programme, season=programme.current_season).order_by('number_in_season').select_related('programme').first()

    def get_absolute_url(self):
        return reverse('programmes:episode_detail', args=[self.programme.slug, self.season, self.number_in_season])

    def save(self, *args, **kwargs):
        # self.slug = slugify(self.title)
        super(Episode, self).save(*args, **kwargs)

    class Meta:
        # unique_together = (('slug', 'programme'), ('season', 'number_in_season', 'programme'))
        unique_together = (('season', 'number_in_season', 'programme'))
        verbose_name = _('episode')
        verbose_name_plural = _('episodes')

    def __unicode__(self):
        return str(self.season) + 'x' + str(self.number_in_season) + ' ' + str(self.programme)


def model_created(sender, **kwargs):
    the_instance = kwargs['instance']
    if kwargs['created']:
        for role in Role.objects.filter(programme=the_instance.programme):
            Participant.objects.create(person=role.person, episode=the_instance, role=role.role, description=role.description)

post_save.connect(model_created, sender=Episode)


class Participant(models.Model):
    person = models.ForeignKey(User, verbose_name=_("person"))
    episode = models.ForeignKey(Episode, verbose_name=_("episode"))
    role = models.CharField(default=NOT_SPECIFIED, verbose_name=_("role"), choices=ROLES, max_length=2)
    description = models.TextField(blank=True, verbose_name=_("description"))

    class Meta:
        unique_together = ('person', 'episode', 'role')
        verbose_name = _('participant')
        verbose_name_plural = _('participants')

    def __unicode__(self):
        return str(self.episode) + ": " + self.person.username




class Role(models.Model):
    person = models.ForeignKey(User, verbose_name=_("person"))
    programme = models.ForeignKey(Programme, verbose_name=_("programme"))
    role = models.CharField(default=NOT_SPECIFIED, verbose_name=_("role"), choices=ROLES, max_length=2)
    description = models.TextField(blank=True, verbose_name=_("description"))
    date_joined = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('person', 'programme', 'role')
        verbose_name = _('role')
        verbose_name_plural = _('roles')
        permissions = (
            ("change_his_role", "Can change his role"),
        )

    def __unicode__(self):
        return self.programme.name + ": " + self.person.username


class Podcast(models.Model):
    episode = models.OneToOneField(Episode, primary_key=True)
    url = models.CharField(max_length=2048)
    mime_type = models.CharField(max_length=20)
    length = models.PositiveIntegerField()  # bytes
    duration = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def get_absolute_url(self):
        return self.episode.get_absolute_url()


