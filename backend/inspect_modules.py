import ast
import os
import json

modules = {
    "Booking": {
        "router": "app/api/v1/booking.py",
        "service": "app/services/booking.py",
        "repository": "app/repositories/booking.py",
        "model": "app/models/booking.py",
        "schema": "app/schemas/booking.py"
    },
    "Prescriptions": {
        "router": "app/api/v1/prescriptions.py",
        "service": "app/services/prescription_service.py",
        "repository": "app/repositories/prescription.py",
        "model": "app/models/prescription.py",
        "schema": "app/schemas/prescription.py"
    },
    "Exercises": {
        "router": "app/api/v1/exercises.py",
        "service": "app/services/exercise_service.py",
        "repository": "app/repositories/exercise.py",
        "model": "app/models/exercise.py",
        "schema": "app/schemas/exercise.py"
    },
    "Audit": {
        "router": "app/api/v1/audit.py",
        "service": "app/services/audit.py",
        "repository": "app/repositories/audit.py",
        "model": "app/models/audit.py",
        "schema": "app/schemas/audit.py"
    },
    "Analytics": {
        "router": "app/api/v1/analytics.py",
        "service": "app/services/analytics.py",
        "repository": "app/repositories/analytics.py",
        "model": "app/models/analytics.py",
        "schema": "app/schemas/analytics.py"
    }
}

report = {}

for mod_name, files in modules.items():
    mod_report = {}
    for layer, filepath in files.items():
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                content = f.read()
            try:
                tree = ast.parse(content)
                classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
                functions = [n.name for n in tree.body if isinstance(n, ast.AsyncFunctionDef) or isinstance(n, ast.FunctionDef)]
                for n in tree.body:
                    if isinstance(n, ast.ClassDef):
                        methods = [m.name for m in n.body if isinstance(m, ast.FunctionDef) or isinstance(m, ast.AsyncFunctionDef)]
                        functions.extend([f"{n.name}.{m}" for m in methods])
                
                # Check for router endpoints explicitly
                endpoints = []
                if layer == "router":
                    for n in tree.body:
                        if isinstance(n, ast.AsyncFunctionDef) or isinstance(n, ast.FunctionDef):
                            for dec in n.decorator_list:
                                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in ['get', 'post', 'put', 'patch', 'delete']:
                                    if hasattr(dec.args[0], 'value'):
                                        endpoints.append(f"{dec.func.attr.upper()} {dec.args[0].value}")
                
                mod_report[layer] = {
                    "exists": True,
                    "classes": classes,
                    "functions": functions,
                    "endpoints": endpoints if layer == "router" else None
                }
            except Exception as e:
                 mod_report[layer] = {"exists": True, "error": str(e)}
        else:
            mod_report[layer] = {"exists": False}
    report[mod_name] = mod_report

print(json.dumps(report, indent=2))
