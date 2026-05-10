from imports import *

# =========================================================
# CONFIG
# =========================================================

SEED  = 42
N_SIM = 100_000

np.random.seed(SEED)

# =========================================================
# LOAD DATA
# =========================================================

with open("data/bet365_champions.json", "r") as f:
    market = json.load(f)

with open("data/group_scenarios.json", "r") as f:
    group_scenarios = json.load(f)

with open("data/classified.json", "r") as f:
    groups_data = json.load(f)

with open("data/combinacoes.json", "r") as f:
    third_combinations = json.load(f)

# =========================================================
# DEBUG: Inspecionar estrutura do group_scenarios
# =========================================================

print("=" * 60)
print("INSPEÇÃO DA ESTRUTURA DE group_scenarios.json")
print("=" * 60)

print(f"\nTipo principal: {type(group_scenarios)}")

if isinstance(group_scenarios, dict):
    print(f"Chaves do dicionário: {list(group_scenarios.keys())}")
    print(f"Total de chaves: {len(group_scenarios)}")
    
    # Mostrar primeira chave e seu tipo
    first_key = list(group_scenarios.keys())[0]
    first_value = group_scenarios[first_key]
    print(f"\nPrimeira chave: '{first_key}'")
    print(f"Tipo do valor: {type(first_value)}")
    
    if isinstance(first_value, dict):
        print(f"Chaves do primeiro valor: {list(first_value.keys())}")
    elif isinstance(first_value, list):
        print(f"Tamanho da lista: {len(first_value)}")
        if len(first_value) > 0:
            print(f"Tipo do primeiro item: {type(first_value[0])}")
            if isinstance(first_value[0], dict):
                print(f"Chaves do primeiro item: {list(first_value[0].keys())}")

elif isinstance(group_scenarios, list):
    print(f"Tamanho da lista: {len(group_scenarios)}")
    if len(group_scenarios) > 0:
        print(f"Tipo do primeiro item: {type(group_scenarios[0])}")
        if isinstance(group_scenarios[0], dict):
            print(f"Chaves do primeiro item: {list(group_scenarios[0].keys())}")
            
            # Verificar se tem 'groups'
            if 'groups' in group_scenarios[0]:
                groups_data_example = group_scenarios[0]['groups']
                print(f"\nTipo de 'groups': {type(groups_data_example)}")
                if isinstance(groups_data_example, dict):
                    first_group = list(groups_data_example.keys())[0]
                    print(f"Primeiro grupo: {first_group}")
                    print(f"Tipo do grupo: {type(groups_data_example[first_group])}")
                    if isinstance(groups_data_example[first_group], dict):
                        print(f"Chaves do grupo: {list(groups_data_example[first_group].keys())}")
                elif isinstance(groups_data_example, list):
                    print(f"Tamanho da lista de grupos: {len(groups_data_example)}")
                    if len(groups_data_example) > 0:
                        print(f"Tipo do primeiro item: {type(groups_data_example[0])}")
                        if isinstance(groups_data_example[0], dict):
                            print(f"Chaves: {list(groups_data_example[0].keys())}")

print("\n" + "=" * 60)
print("FIM DA INSPEÇÃO")
print("=" * 60 + "\n")

# Aguardar input do usuário para continuar
input("Pressione Enter para continuar com a simulação...")