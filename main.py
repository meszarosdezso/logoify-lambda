import boto3
import os
import dotenv

from dataclasses import dataclass
from io import BufferedRandom, BytesIO
from PIL import Image, ImageChops
from rembg import remove as remove_bg


dotenv.load_dotenv()

session = boto3.Session(
    os.getenv("aws_access_key_id"),
    os.getenv("aws_secret_access_key"),
)

s3 = session.resource("s3")
bucket = s3.Bucket(os.getenv('aws_s3_bucket'))


def download_from_s3(key: str, file: BufferedRandom) -> BufferedRandom:
    bucket.download_fileobj(key, file)
    return file


def upload_to_s3(key: str, byte_array: bytes):
    bucket.put_object(
        ACL='public-read',
        Body=byte_array,
        Key=key,
    )


def trim_image(im: Image):
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    pass


def handler(event):
    key = event.queryStringParameters['key']
    id, name, type, *_ = key.split("/")
    path = f'/tmp/{name}.{type}'

    file = open(path, 'ab+')
    download_from_s3(key, file)

    image: Image = Image.open(file)
    image = remove_bg(image)
    image = trim_image(image)

    image_bytes = BytesIO()
    image.save(image_bytes, format='webp')

    file.close()

    output_key = f'{id}/{name}_logoified.webp'
    upload_to_s3(output_key, image_bytes.getvalue())

    url = f'https://{bucket.name}.s3.{os.getenv("aws_region")}.amazonaws.com/{output_key}'

    return {
        'statusCode': 201,
        'url': url,
    }
