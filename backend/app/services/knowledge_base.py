
# import os
# from app.services.rag_service import add_documents

# def initialize_knowledge_base():
#     data_dir = "backend/data"
#     for filename in os.listdir(data_dir):
# import os
# from app.services.rag_service import add_documents

# def initialize_knowledge_base():
#     data_dir = "backend/data"
#     for filename in os.listdir(data_dir):
#         if filename.endswith(".md"):
#             with open(os.path.join(data_dir, filename), "r") as f:
#                 add_documents([f.read()])



import os
import asyncio
from app.services.rag_service import add_documents

async def initialize_knowledge_base():
    # current file path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # do levels upar jao: services -> app -> backend
    data_dir = os.path.join(base_dir, "..", "..", "data")
    data_dir = os.path.normpath(data_dir)

    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        return

    print(f"📂 Loading knowledge base from: {data_dir}")

    tasks = []
    for filename in os.listdir(data_dir):
        if filename.endswith(".md"):
            file_path = os.path.join(data_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    tasks.append(add_documents([content]))
                    print(f"✅ Queued for loading: {filename}")
            except Exception as e:
                print(f"❌ Failed to read {filename}: {e}")
    
    if tasks:
        await asyncio.gather(*tasks)
        print("✅ Knowledge base loading complete.")