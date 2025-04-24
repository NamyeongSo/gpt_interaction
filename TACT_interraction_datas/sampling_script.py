import json
import random

# Load the JSON file
file_path = r"C:/Users/namyeong/Desktop/revision/human_llm_intetraction/TACT_SLURP_guide_diverse_flows_20250416.json"

with open(file_path, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

# Check the type of data structure
print(f"Data type: {type(data)}")
if isinstance(data, list):
    print(f"Total items: {len(data)}")
elif isinstance(data, dict):
    print(f"Number of keys: {len(data.keys())}")
    print(f"Keys: {list(data.keys())[:5]} ...")

# Convert data to list if it's a dictionary
if isinstance(data, dict):
    items = list(data.items())
else:
    items = data

# Calculate how many unique items we can sample
total_needed = 9 * 4  # 36 items total
available_items = len(items)
print(f"Total items needed: {total_needed}, Available items: {available_items}")

if available_items < total_needed:
    print(f"Warning: Not enough items. Can only create {available_items // 9} complete samples of 9 items each.")
    # Use as many items as possible
    num_samples = min(4, available_items // 9)
    items_per_sample = 9
else:
    num_samples = 4
    items_per_sample = 9

# Randomly sample without replacement for all samples
# This ensures no duplicates across all samples
random.shuffle(items)
all_sampled_items = items[:num_samples * items_per_sample]

# Create samples
samples = []
for i in range(num_samples):
    start_idx = i * items_per_sample
    end_idx = start_idx + items_per_sample
    sample = all_sampled_items[start_idx:end_idx]
    samples.append(sample)

# Save each sample to a separate JSON file
for i, sample in enumerate(samples, 1):
    output_file = f"sample_{i}.json"
    
    # Convert back to dictionary if original data was a dictionary
    if isinstance(data, dict):
        sample_dict = dict(sample)
        output_data = sample_dict
    else:
        output_data = sample
    
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(sample)} items to {output_file} (no duplicates between samples)") 