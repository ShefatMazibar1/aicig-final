"""
Direct file patch for gradio_client/utils.py
Run once at build time via: python patch_gradio.py
Fixes: TypeError: argument of type 'bool' is not iterable
       APIInfoParseError: Cannot parse schema True
"""
import sys
import os


def patch_utils():
    import gradio_client
    utils_path = os.path.join(os.path.dirname(gradio_client.__file__), "utils.py")
    print(f"Patching: {utils_path}")

    with open(utils_path, "r") as f:
        content = f.read()

    old = 'def _json_schema_to_python_type(schema: Any, defs) -> str:\n    """Convert the json schema into a python type hint"""\n    if schema == {}:\n        return "Any"\n    type_ = get_type(schema)'

    new = 'def _json_schema_to_python_type(schema: Any, defs) -> str:\n    """Convert the json schema into a python type hint"""\n    if not isinstance(schema, dict):\n        return "Any"\n    if schema == {}:\n        return "Any"\n    if "additionalProperties" in schema and not isinstance(schema.get("additionalProperties"), dict):\n        schema = {k: v for k, v in schema.items() if k != "additionalProperties"}\n    type_ = get_type(schema)'

    if old in content:
        content = content.replace(old, new)
        with open(utils_path, "w") as f:
            f.write(content)
        print("✓ gradio_client/utils.py patched")
    elif "if not isinstance(schema, dict):" in content:
        print("✓ gradio_client/utils.py already patched")
    else:
        print("✗ Could not find patch target in utils.py")
        sys.exit(1)


def patch_routes():
    """Patch gradio/routes.py to catch APIInfoParseError gracefully."""
    import gradio
    routes_path = os.path.join(os.path.dirname(gradio.__file__), "routes.py")
    print(f"Patching: {routes_path}")

    with open(routes_path, "r") as f:
        content = f.read()

    old = "    gradio_api_info = api_info(False)"
    new = "    try:\n        gradio_api_info = api_info(False)\n    except Exception as _e:\n        print(f'api_info error (non-fatal): {_e}')\n        gradio_api_info = {}"

    if old in content:
        content = content.replace(old, new)
        with open(routes_path, "w") as f:
            f.write(content)
        print("✓ gradio/routes.py patched")
    elif "api_info error (non-fatal)" in content:
        print("✓ gradio/routes.py already patched")
    else:
        print("⚠ Could not find routes.py patch target (non-fatal, continuing)")


if __name__ == "__main__":
    patch_utils()
    patch_routes()
    print("All patches applied successfully")
