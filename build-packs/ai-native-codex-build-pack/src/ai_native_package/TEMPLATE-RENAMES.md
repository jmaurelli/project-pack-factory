# Template Rename Checklist

After copying this package root, rename the following in one controlled pass:

1. Distribution name
   - Update `pyproject.toml` `project.name`
   - Update `DISTRIBUTION_NAME` in `__about__.py`

2. Python module name
   - Rename `src/ai_native_package/`
   - Update import paths and `MODULE_NAME` / `PACKAGE_NAME`
   - Update `tool.setuptools.packages.find.include`

3. Console script name
   - Update `project.scripts` in `pyproject.toml`
   - Update docs and prompt references

4. Package-root references
   - Update the package path in `README.md`
   - Update all files under `prompts/`

5. Domain defaults
   - Update default `output_dir`
   - Update `operation_class`
   - Update any prompt wording that should become domain-specific

Keep these items stable unless you intentionally need different behavior:
- thin CLI entrypoint pattern
- delegated backend planning shape
- `intent = "execution_only"`
- `delegation_mode = "codex_worker"`
- focused scaffold test strategy
