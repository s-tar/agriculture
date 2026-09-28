import argparse
import asyncio
import math
import random

from faker import Faker
from src.config.settings import settings
from src.domain.value_objects.geometry import Geometry, GeometryType, Point
from src.infrastructure.repository.sqlmodel.database import (
    get_session,
)
from src.infrastructure.repository.sqlmodel.unit_of_work import SqlModelUnitOfWork

BATCH_SIZE = 500
METERS_IN_DEGREE = 111_320.0


CROPS = [
    # cereals
    "Пшениця озима",
    "Пшениця яра",
    "Ячмінь озимий",
    "Ячмінь ярий",
    "Жито озиме",
    "Жито яре",
    "Овес",
    "Тритикале",
    "Кукурудза",
    "Сорго зернове",
    "Просо",
    "Гречка",
    "Чумиза",
    "Амарант зерновий",
    # oilseeds
    "Соняшник",
    "Ріпак озимий",
    "Ріпак ярий",
    "Соя",
    "Льон олійний",
    "Льон прядивний",
    "Коноплі",
    "Гірчиця біла",
    "Гірчиця сиза",
    "Сафлор",
    "Рижій",
    "Кунжут",
    # legumes
    "Горох",
    "Квасоля",
    "Нут",
    "Сочевиця",
    "Вика яра",
    "Вика озима",
    "Люпин білий",
    "Люпин жовтий",
    "Люпин вузьколистий",
    "Боби кормові",
    "Чина",
    # root / tuber
    "Буряк цукровий",
    "Буряк кормовий",
    "Картопля",
    "Морква",
    "Пастернак",
    "Цибуля ріпчаста",
    "Часник",
    "Топінамбур",
    # vegetables
    "Капуста білоголова",
    "Капуста цвітна",
    "Капуста брокколі",
    "Капуста кольрабі",
    "Томат",
    "Перець солодкий",
    "Перець гострий",
    "Баклажан",
    "Огірок",
    "Гарбуз",
    "Кабачок",
    "Патисон",
    "Буряк столовий",
    "Редька",
    "Редиска",
    "Цибуля зелена",
    "Цибуля-порей",
    "Шпинат",
    "Салат листовий",
    "Щавель",
    # forage
    "Кукурудза (силос)",
    "Соняшник (силос)",
    "Сорго цукрове",
    "Суданська трава",
    "Люцерна",
    "Конюшина червона",
    "Конюшина біла",
    "Тимофіївка лучна",
    "Костриця лучна",
    "Костриця очеретяна",
    "Райграс однорічний",
    "Райграс багаторічний",
    "Пажитниця",
    "Стоколос",
    "Еспарцет",
    # herbs / spices
    "Петрушка",
    "Кріп",
    "Кінза",
    "Базилік",
    "Чебрець",
    "М'ята",
    "Меліса",
    "Естрагон",
    "Кмин",
    "Коріандр",
    "Аніс",
    "Фенхель",
    "Ромашка аптечна",
    "Валеріана",
    "Звіробій",
    "Кропива",
    # industrial / other
    "Цукрова тростина",
    "Тютюн",
    "Хмель",
    "Лаванда",
    "Ехінацея",
    "Стевія",
]

fake = Faker("uk_UA")
Faker.seed(42)

CROP_MAP = {}
OWNER_MAP = {}

owners_added = 0
fields_added = 0


def generate_owner_name() -> str:
    return f"{fake.last_name()} {fake.first_name()[0]}.{fake.middle_name()[0]}."


def get_point_on_distance(
    lon: float, lat: float, distance: float, angle: float
) -> tuple[float, float]:
    lon_meter_in_degrees = METERS_IN_DEGREE * math.cos(math.radians(lat))
    point_lon = lon + distance * math.cos(angle) / lon_meter_in_degrees
    point_lat = lat + distance * math.sin(angle) / METERS_IN_DEGREE

    return (point_lon - 180) % 360 - 180, point_lat


def generate_geometry(
    target_area_ha: float, spawn_radius: float, spawn_point: tuple[float, float] | None
) -> Geometry:
    if spawn_point:
        spawn_lat, spawn_lon = spawn_point
    else:
        spawn_lon = random.uniform(24.0, 38.0)
        spawn_lat = random.uniform(45.0, 51.5)

    spawn_lat = min(max(spawn_lat, -65.0), 65.0)

    field_center_distance = spawn_radius * math.sqrt(random.random())
    field_center_angle = random.uniform(0, 2 * math.pi)

    field_center_lon, field_center_lat = get_point_on_distance(
        lon=spawn_lon,
        lat=spawn_lat,
        distance=field_center_distance,
        angle=field_center_angle,
    )

    number_of_points = random.randint(4, 5)
    angles = sorted(
        [random.uniform(i * math.pi / 2, (i + 1) * math.pi / 2) for i in range(4)]
        + [random.uniform(0, 2 * math.pi) for _ in range(number_of_points - 4)]
    )

    field_radius = math.sqrt(target_area_ha * 10_000 / math.pi)
    coordinated = []
    for angle in angles:
        point_lon, point_lat = get_point_on_distance(
            lon=field_center_lon,
            lat=field_center_lat,
            distance=field_radius,
            angle=angle,
        )
        coordinated.append(Point(lon=point_lon, lat=point_lat))

    return Geometry(
        type=GeometryType.POLYGON,
        coordinates=coordinated,
    )


async def seed_fields(
    amount: int,
    spawn_radius: float,
    spawn_point: tuple[float, float] | None,
) -> None:
    async for session in get_session():
        uow = SqlModelUnitOfWork(session=session, srid=settings.SRID)
        existed_field_amount = await uow.fields.count()
        field_number = existed_field_amount + 1
        added_fields_count = 0
        for i in range(math.ceil(amount / BATCH_SIZE)):
            for j in range(BATCH_SIZE):
                if BATCH_SIZE * i + j >= amount:
                    break

                geometry = generate_geometry(
                    target_area_ha=random.uniform(1.0, 100.0),
                    spawn_point=spawn_point,
                    spawn_radius=spawn_radius,
                )

                await uow.fields.create(
                    name=f"Поле №{field_number}",
                    owner_name=generate_owner_name(),
                    crop_name=random.choice(CROPS),
                    geometry=geometry,
                )
                field_number += 1
                added_fields_count += 1

            await uow.commit()
            print(f"Added {added_fields_count} fields")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the agriculture database")
    parser.add_argument(
        "--fields",
        type=int,
        default=1000,
        metavar="N",
        help="Number of fields to create (default: 1000)",
    )

    parser.add_argument(
        "--spawn-point", type=float, nargs=2, metavar=("LAT", "LON"), help="Spawn point"
    )
    parser.add_argument(
        "--spawn-radius",
        type=float,
        metavar="METERS",
        default=10_000.0,
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
