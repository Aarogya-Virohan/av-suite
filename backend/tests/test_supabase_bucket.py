from app.core.storage import storage_client
print("Testing Supabase SDK")
try:
    # Just checking what methods exist
    print(dir(storage_client.client.storage.from_("documents")))
except Exception as e:
    print(e)
