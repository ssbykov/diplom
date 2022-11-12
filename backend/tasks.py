from celery import shared_task

import yaml
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.utils import IntegrityError

from backend.models import User, Shop, Category, ProductInfo, Product, ProductParameter, Parameter
from yaml.loader import SafeLoader
from pathlib import Path


@shared_task
def sand_mail(user_id, msg_txt, topic_msg):
    sand_mail_import(user_id, msg_txt, topic_msg)


def sand_mail_import(user_id, msg_txt, topic_msg):
    """
    отправяем письмо при выполнении импорта
    """
    user = User.objects.get(id=user_id)
    msg = EmailMultiAlternatives(
        # title:
        topic_msg,
        # message:
        msg_txt,
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [user.email]
    )
    msg.send()


@shared_task
def do_import(filename, user_id):
    topic_msg = 'результат импорта данных'
    file_path = Path(__file__).parent.absolute()
    try:
        with open(str(file_path) + filename, encoding='UTF-8') as yml:
            data = yaml.load(yml, Loader=SafeLoader)
    except FileNotFoundError as e:
        sand_mail_import(user_id, f'При импорте файла {filename} возникла ошибка {str(e)}', topic_msg)
    else:
        try:
            shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=user_id)
        except IntegrityError as e:
            sand_mail_import(user_id, f'При импорте файла {filename} возникла ошибка {str(e)}', topic_msg)
            return
        for category in data['categories']:
            category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
            category_object.shops.add(shop.id)
            category_object.save()
        ProductInfo.objects.filter(shop_id=shop.id).delete()
        for item in data['goods']:
            product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

            product_info = ProductInfo.objects.create(product_id=product.id,
                                                      model=item['model'],
                                                      price=item['price'],
                                                      price_rrc=item['price_rrc'],
                                                      quantity=item['quantity'],
                                                      shop_id=shop.id)
            for name, value in item['parameters'].items():
                parameter_object, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(product_info_id=product_info.id,
                                                parameter_id=parameter_object.id,
                                                value=value)

        sand_mail_import(user_id, f'Файл с данными {filename} успешно импортирован.', topic_msg)
