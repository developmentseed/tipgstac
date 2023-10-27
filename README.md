
<p align="center">
  <img width="500" alt="tipgstac" src="https://github.com/developmentseed/tipgstac/assets/10407788/ed8e075d-be83-4267-bcdf-19641c3a013a">
  <p align="center">A PgSTAC Backend for TiPG.</p>
</p>


---

**Documentation**:

**Source Code**: <a href="https://github.com/developmentseed/tipgstac" target="_blank">https://github.com/developmentseed/tipgstac</a>

---

Create a simple STAC API using [`TiPg`](https://github.com/developmentseed/tipg) and [PgSTAC](https://github.com/stac-utils/pgstac) database. The API should be OGC Features compliant (see: https://github.com/developmentseed/tipg#ogc-specifications)

## Install

```bash
git clone https://github.com/developmentseed/tipgstac.git
cd tipgstac

python -m pip install -e .
```

### Configuration

To be able to work, the application will need access to the database. `tipgstac` uses [Starlette](https://www.starlette.io/config/)'s configuration pattern, which makes use of environment variables or a `.env` file to pass variables to the application.

An example of a `.env` file can be found in [.env.example](https://github.com/developmentseed/tipgstac/blob/main/.env.example)

```
# you need to define the DATABASE_URL directly
DATABASE_URL=postgresql://username:password@0.0.0.0:5432/postgis
```

## Launch

```bash
$ pip install uvicorn

# Set your PostGIS database instance URL in the environment
$ export DATABASE_URL=postgresql://username:password@0.0.0.0:5432/postgis
$ uvicorn tipgstac.main:app

# or using Docker

$ docker-compose up app
```

<p align="center">
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/ea1aae7e-6992-4cec-a59f-4897d1afff76">
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/faea4b8d-c22f-4e21-9044-8c69fc7a8393">
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/68069644-c3cf-411e-a500-7236f4274c71">
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/aa3062ba-6bfb-4c58-9ae1-a3726f8f4f95">
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/d4e6615f-f3a8-48b6-922c-8854383d24ff">
</p>

## Contribution & Development

See [CONTRIBUTING.md](https://github.com/developmentseed/tipgstac/blob/main/CONTRIBUTING.md)

## License

See [LICENSE](https://github.com/developmentseed/tipgstac/blob/main/LICENSE)

## Authors

Created by [Development Seed](<http://developmentseed.org>)

## Changes

See [CHANGES.md](https://github.com/developmentseed/tipgstac/blob/main/CHANGES.md).

