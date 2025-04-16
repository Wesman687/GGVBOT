import dotenv
from huggingface_hub import login
from transformers import AutoTokenizer, AutoModelForCausalLM

# Step 1: Authenticate with Hugging Face
HUGGING_FACES = dotenv.get("HUGGING_FACES")
login(HUGGING_FACES)

# Step 2: Load the tokenizer and model
model_id = "meta-llama/Llama-4-Scout-17B-16E"
tokenizer = AutoTokenizer.from_pretrained(model_id, token=True)
model = AutoModelForCausalLM.from_pretrained(model_id, token=True)

# Step 3: Generate text
prompt = "Your prompt here"
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))