try:
    import univention.testing.conftest  # noqa: F401
except ImportError:
    pytest_plugins = ["univention.testing.ucsschool.conftest"]
else:
    pytest_plugins = ["univention.testing.conftest", "univention.testing.ucsschool.conftest"]
