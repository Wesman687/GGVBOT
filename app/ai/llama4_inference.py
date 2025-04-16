# from transformers import AutoTokenizer, AutoModelForCausalLM
# import torch

# model_id = "meta-llama/Llama-4-Scout-17B-16E"
# tokenizer = AutoTokenizer.from_pretrained(model_id)
# model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto", torch_dtype=torch.float16)

# def run_llama4_inference(prompt: str, max_tokens: int = 256) -> str:
#     inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
#     output = model.generate(
#         **inputs,
#         max_new_tokens=max_tokens,
#         do_sample=False,
#         temperature=0.2,
#         pad_token_id=tokenizer.eos_token_id
#     )
#     return tokenizer.decode(output[0], skip_special_tokens=True).strip()
