import kreview

def test_import():
    """Verify the package can be successfully imported."""
    assert kreview.__version__ is not None
