
<p align="center">
  <img width="500" alt="tipgstac" src="https://github.com/developmentseed/tipgstac/assets/10407788/1269b5e4-e4a2-454c-9b4b-14734ae76a8f">
  <p align="center">A PgSTAC Backend for TiPG.</p>
</p>

<p align="center">
  <a href="https://github.com/developmentseed/tipgstac/actions?query=workflow%3ACI" target="_blank">
      <img src="https://github.com/developmentseed/titiler/workflows/CI/badge.svg" alt="Test">
  </a>
  <a href="https://github.com/developmentseed/tipgstac/blob/main/LICENSE" target="_blank">
      <img src="https://img.shields.io/github/license/developmentseed/tipgstac.svg" alt="License">
  </a>
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
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/9663691b-b63d-42e2-a0d4-974a0cbc6b2b">
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/bc1709e3-da1c-440e-bd5d-a9ba7e29ba76">
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/b3f11f21-ac87-4121-8650-a033ed24dbd8">
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/f366c5b8-c92c-49ad-8d3b-464e77c4a3cf">
  <img width="500" src="https://github.com/developmentseed/tipgstac/assets/10407788/deb0658d-02c4-4dd0-a05c-b2a14180472d">
</p>



## Contribution & Development

See [CONTRIBUTING.md](https://github.com/developmentseed/tipgstac/blob/main/CONTRIBUTING.md)

## License

See [LICENSE](https://github.com/developmentseed/tipgstac/blob/main/LICENSE)

## Authors

Created by [Development Seed](<http://developmentseed.org>)

## Changes

See [CHANGES.md](https://github.com/developmentseed/tipgstac/blob/main/CHANGES.md).

