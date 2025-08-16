import json

# Читаем universities.json
with open('universities.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Всего записей: {len(data)}")

# Получаем уникальные специальности
unique_specs = set()
for item in data:
    if 'specialization' in item and item['specialization']:
        unique_specs.add(item['specialization'])

print(f"Уникальных специальностей: {len(unique_specs)}")
print("\nСписок специальностей:")
for spec in sorted(unique_specs):
    print(f"- {spec}")

# Проверяем количество специальностей для каждого вуза
print("\nКоличество специальностей по вузам:")
uni_specs = {}
for item in data:
    if 'name' in item and 'specialization' in item:
        uni_name = item['name']
        if uni_name not in uni_specs:
            uni_specs[uni_name] = set()
        uni_specs[uni_name].add(item['specialization'])

for uni, specs in sorted(uni_specs.items()):
    print(f"{uni}: {len(specs)} специальностей")

# Проверяем, есть ли все 8 специальностей
expected_specs = {
    "Программная инженерия",
    "Data Science",
    "UX/UI дизайн", 
    "Кибербезопасность",
    "DevOps инженерия",
    "Мобильная разработка",
    "Game Development",
    "AI/ML инженерия"
}

missing_specs = expected_specs - unique_specs
if missing_specs:
    print(f"\n❌ Отсутствуют специальности: {missing_specs}")
else:
    print(f"\n✅ Все 8 специальностей присутствуют!")

# Проверяем, есть ли лишние специальности
extra_specs = unique_specs - expected_specs
if extra_specs:
    print(f"⚠️ Лишние специальности: {extra_specs}") 