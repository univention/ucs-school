Developer docu for building the UCS\@school Kelvin REST API
===========================================================

The Univention style is brought in by the git submodule ``sphinx-univention``.

HTML is built using a Docker container with Sphinx: https://github.com/keimlink/docker-sphinx-doc

Initial docs
------------

The initial ``docs`` content was created with::

    $ docker run -u "$(id -u):$(id -g)" -it --rm -v "$(pwd)/docs":/home/python/docs keimlink/sphinx-doc:1.7.1 sphinx-quickstart docs

You don't have to do this anymore. This is here just for documentations sake.

Build HTML output from RST files
--------------------------------

Don't use the ``sphinx-univention`` for this. It's outdated. Use a local ``sphinx`` version
instead and checkout the git submodule with ``git submodule update --init --recursive --remote``.

To build the HTML documentation run::

    $ cd doc/kelvin
    $ make -C docs html


Autobuild HTML docs during development
--------------------------------------

To have the HTML output served at http://127.0.0.1:8000 and auto-rebuild when a file is changed, do the following:

Build a Docker image (execute only once)::

    $ docker build -t sphinx-autobuild --file Dockerfile_autobuild .

You should have a Docker image of about 150 MB now.
Check with ``docker images sphinx-autobuild``.

Now start a Docker container that will build and serve the docs at http://127.0.0.1:8000::

    $ docker run -u "$(id -u):$(id -g)" -it -p 8000:8000 --rm -v "$(pwd)/docs":/home/python/docs sphinx-autobuild

To stop the container hit ``Ctrl-C``.

Publish HTML documentation
--------------------------

After building the HTML files (see section ``Build HTML output from RST files`` above) the result has to be published.
Add the files to the docs git repository and start a Jenkins job::

    $ rsync -av --delete docs/_build/html/ ~/git/docs.univention.de/ucsschool-kelvin-rest-api/
    $ cd ~/git/docs.univention.de/
    $ git add -u
    $ git commit -m "Bug #52220: update Kelvin API documentation"
    $ git push


The documentation will be build automatically in our [pipeline](https://git.knut.univention.de/univention/docs.univention.de/-/pipelines).
You have to press a deploy button to publish the documentation.
