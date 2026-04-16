"""
Direct file patch for gradio_client/utils.py
Run once at build time via: python patch_gradio.py
Fixes: TypeError: argument of type 'bool' is not iterable
"""
import sys
import importlib

def patch():
    import gradio_client.utils as gcu
    import gradio_client
    import os

    utils_path = os.path.join(os.path.dirname(gradio_client.__file__), "utils.py")
    print(f"Patching: {utils_path}")

    with open(utils_path, "r") as f:
        content = f.read()

    # The buggy line passes additionalProperties (which can be bool) directly
    # into _json_schema_to_python_type. We patch _json_schema_to_python_type
    # to guard against non-dict input at the very top of the function.

    old = '''def _json_schema_to_python_type(schema: Any, defs) -> str:
    """Convert the json schema into a python type hint\"""
    if schema == {}:
        return "Any"
    type_ = get_type(schema)'''

    new = '''def _json_schema_to_python_type(schema: Any, defs) -> str:
    """Convert the json schema into a python type hint\"""
    if not isinstance(schema, dict):
        return "Any"
    if schema == {}:
        return "Any"
    if "additionalProperties" in schema and not isinstance(schema.get("additionalProperties"), dict):
        schema = {k: v for k, v in schema.items() if k != "additionalProperties"}
    type_ = get_type(schema)'''

    if old in content:
        content = content.replace(old, new)
        with open(utils_path, "w") as f:
            f.write(content)
        print("✓ Patch applied successfully")
    elif "if not isinstance(schema, dict):" in content:
        print("✓ Already patched, skipping")
    else:
        print("✗ Could not find patch target - manual fix needed")
        sys.exit(1)

if __name__ == "__main__":
    patch()
