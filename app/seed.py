import argparse
import asyncio
import math
import random
import sys
import uuid

from faker import Faker
from pathlib import Path

from geoalchemy2 import functions
from geoalchemy2 import Geography
from sqlalchemy import func
from sqlmodel import cast

from src.core.config import settings
from src.models.field import Field


from sqlmodel import select

from src.core.database import async_session_maker
from src.models.crop import Crop
from src.models.owner import Owner

BATCH_SIZE = 500
METERS_IN_DEGREE = 111_320.0


CROPS = [
    # cereals
    "Пшениця озима", "Пшениця яра", "Ячмінь озимий", "Ячмінь ярий",
    "Жито озиме", "Жито яре", "Овес", "Тритикале", "Кукурудза",
    "Сорго зернове", "Просо", "Гречка", "Чумиза", "Амарант зерновий",
    # oilseeds
    "Соняшник", "Ріпак озимий", "Ріпак ярий", "Соя", "Льон олійний",
    "Льон прядивний", "Коноплі", "Гірчиця біла", "Гірчиця сиза",
    "Сафлор", "Рижій", "Кунжут",
    # legumes
    "Горох", "Квасоля", "Нут", "Сочевиця", "Вика яра", "Вика озима",
    "Люпин білий", "Люпин жовтий", "Люпин вузьколистий", "Боби кормові", "Чина",
    # root / tuber
    "Буряк цукровий", "Буряк кормовий", "Картопля", "Морква", "Пастернак",
    "Цибуля ріпчаста", "Часник", "Топінамбур",
    # vegetables
    "Капуста білоголова", "Капуста цвітна", "Капуста брокколі", "Капуста кольрабі",
    "Томат", "Перець солодкий", "Перець гострий", "Баклажан", "Огірок",
    "Гарбуз", "Кабачок", "Патисон", "Буряк столовий", "Редька", "Редиска",
    "Цибуля зелена", "Цибуля-порей", "Шпинат", "Салат листовий", "Щавель",
    # forage
    "Кукурудза (силос)", "Соняшник (силос)", "Сорго цукрове", "Суданська трава",
    "Люцерна", "Конюшина червона", "Конюшина біла", "Тимофіївка лучна",
    "Костриця лучна", "Костриця очеретяна", "Райграс однорічний",
    "Райграс багаторічний", "Пажитниця", "Стоколос", "Еспарцет",
    # herbs / spices
    "Петрушка", "Кріп", "Кінза", "Базилік", "Чебрець", "М'ята", "Меліса",
    "Естрагон", "Кмин", "Коріандр", "Аніс", "Фенхель", "Ромашка аптечна",
    "Валеріана", "Звіробій", "Кропива",
    # industrial / other
    "Цукрова тростина", "Тютюн", "Хмель", "Лаванда", "Ехінацея", "Стевія",
]

fake = Faker("uk_UA")
Faker.seed(42)

CROP_MAP = {}
OWNER_MAP = {}

owners_added = 0
fields_added = 0

def generate_owner_name() -> str:
    return f"{fake.last_name()} {fake.first_name()[0]}.{fake.middle_name()[0]}."

async def get_random_crop(session) -> Crop:
    global CROP_MAP

    crop_name = random.choice(CROPS)
    crop = CROP_MAP.get(crop_name)
    if not crop:
        crop = (await session.exec(select(Crop).where(Crop.name == crop_name))).first()

    if not crop:
        crop = Crop(name=crop_name)
        session.add(crop)
        await session.flush()
        await session.refresh(crop)

    CROP_MAP[crop_name] = crop
    return crop

async def get_random_owner(session) -> Crop:
    global OWNER_MAP
    owner_name = generate_owner_name()
    owner = OWNER_MAP.get(owner_name)
    if not owner:
        owner = (await session.exec(select(Owner).where(Owner.name == owner_name))).first()

    if not owner:
        owner = Owner(name=owner_name)
        session.add(owner)
        await session.flush()
        await session.refresh(owner)

    OWNER_MAP[owner.name] = owner
    return owner


def get_point_on_distance(lon: float, lat: float, distance: float, angle: float) -> tuple[float, float]:
    lon_meter_in_degrees = METERS_IN_DEGREE * math.cos(math.radians(lat))
    point_lon = lon + distance * math.cos(angle) / lon_meter_in_degrees
    point_lat = lat + distance * math.sin(angle) / METERS_IN_DEGREE

    return (point_lon - 180) % 360 - 180, point_lat


def generate_polygon_wkt(
    target_area_ha: float,
    spawn_radius: float,
    spawn_point: tuple[float, float] | None
) -> str:
    if spawn_point:
        spawn_lat, spawn_lon = spawn_point
    else:
        spawn_lon = random.uniform(24.0, 38.0)
        spawn_lat = random.uniform(45.0, 51.5)

    spawn_lat = min(max(spawn_lat, -65.0), 65.0)

    field_center_distance = spawn_radius * math.sqrt(random.random())
    field_center_angle = random.uniform(0,  2 * math.pi)

    field_center_lon, field_center_lat = get_point_on_distance(
        lon=spawn_lon, lat=spawn_lat, distance=field_center_distance, angle=field_center_angle,
    )

    number_of_points = random.randint(4, 5)
    angles = sorted(
        [random.uniform(i * math.pi / 2, (i + 1) * math.pi / 2) for i in range(4)] +
        [random.uniform(0, 2 * math.pi) for _ in range(number_of_points - 4)]
    )

    field_radius = math.sqrt(target_area_ha * 10_000 / math.pi)
    polygon = []
    for angle in angles:
        point_lon, point_lat = get_point_on_distance(
            lon=field_center_lon, lat=field_center_lat, distance=field_radius, angle=angle,
        )
        polygon.append(f"{point_lon:.8f} {point_lat:.8f}")

    polygon.append(polygon[0])
    return f"POLYGON(({', '.join(polygon)}))"


async def seed_fields(
    amount: int,
    spawn_radius: float,
    spawn_point: tuple[float, float] | None,
) -> None:
    async with async_session_maker() as session:
        existed_field_amount = (await session.exec(select(func.count(Field.id)))).one()
        field_number = existed_field_amount +  1
        added_fields_count = 0
        for i in range(math.ceil(amount / BATCH_SIZE)):
            for j in range(BATCH_SIZE):
                if BATCH_SIZE * i + j >= amount:
                    break

                crop = await get_random_crop(session)
                owner = await get_random_owner(session)

                geometry_wkt = generate_polygon_wkt(
                    target_area_ha=random.uniform(1.0, 100.0),
                    spawn_point=spawn_point,
                    spawn_radius=spawn_radius,
                )
                geom = functions.ST_GeomFromText(geometry_wkt)
                session.add(
                    Field(
                        name=f"Поле №{field_number}",
                        geometry=geom,
                        area_ha=functions.ST_Area(cast(geom, Geography(srid=settings.SRID))) / 10_000,
                        crop_id=crop.id,
                        owner_id=owner.id,
                    )
                )
                field_number += 1
                added_fields_count += 1

            await session.commit()
            print(f"Added {added_fields_count} fields")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the agriculture database")
    parser.add_argument(
        "--fields", type=int, default=1000, metavar="N",
        help="Number of fields to create (default: 1000)",
    )

    parser.add_argument(
        '--spawn-point', type=float, nargs=2, metavar=('LAT', 'LON'),
        help="Spawn point"
    )
    parser.add_argument(
        '--spawn-radius', type=float, metavar='METERS', default=10_000.0,
        help="Spawn radius (default: 10 000)",
    )
    args = parser.parse_args()

    await seed_fields(
        amount=args.fields,
        spawn_point=tuple(args.spawn_point) if args.spawn_point else None,
        spawn_radius=args.spawn_radius,
    )

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())