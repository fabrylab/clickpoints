Make Release
============

Making a release consists of three parts:

- raising the version number in `pyproject.toml` and commit the change
- create a new release in github https://github.com/fabrylab/clickpoints/releases/new with this version number as a tag

There is an automatic github action that will publish the release on pypi.
