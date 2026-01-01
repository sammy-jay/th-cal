import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import numpy as np
import random
import os
import datetime

# --- CONFIGURATION ---
FLUID = 'Water'

def get_input(prompt, min_val=0.1):
    """Handles manual user input with validation."""
    while True:
        try:
            val = float(input(f"➤ {prompt}: ").strip())
            if val < min_val:
                print(f"  ⚠️ Value must be > {min_val}.")
                continue
            return val
        except ValueError:
            print("  ⚠️ Please enter a numerical value.")

# --- THERMODYNAMIC ENGINE ---
def analyze_throttling(p1_kpa, t1_c, p2_kpa, t2_c, case_name):
    """
    Performs calculations based on provided logic:
    1. Lookup Hf, Hfg @ P1 
    2. Lookup Tsat, H @ P2 
    3. Determine state 
    4. Solve for X 
    """
    p1_pa, p2_pa = p1_kpa * 1000.0, p2_kpa * 1000.0
    t2_k = t2_c + 273.15

    try:
        # Step 1: Before Throttling - Table A-5 Lookups at P1 
        hf_p1 = CP.PropsSI('H', 'P', p1_pa, 'Q', 0, FLUID) / 1000.0
        hg_p1 = CP.PropsSI('H', 'P', p1_pa, 'Q', 1, FLUID) / 1000.0
        hfg_p1 = hg_p1 - hf_p1
        tsat_p1 = CP.PropsSI('T', 'P', p1_pa, 'Q', 0, FLUID) - 273.15

        # Step 2: After Throttling - Lookup Tsat and H at P2 
        tsat_p2 = CP.PropsSI('T', 'P', p2_pa, 'Q', 0, FLUID) - 273.15
        h2 = CP.PropsSI('H', 'P', p2_pa, 'T', t2_k, FLUID) / 1000.0
        s2 = CP.PropsSI('S', 'P', p2_pa, 'T', t2_k, FLUID) / 1000.0
        v2 = 1.0 / CP.PropsSI('D', 'P', p2_pa, 'T', t2_k, FLUID)

        # Step 3: Conclude Steam State 
        if t2_c > tsat_p2 + 0.5:
            state = "Superheated steam"
        elif t2_c < tsat_p2 - 0.5:
            state = "Wet steam"
        else:
            state = "Saturated steam"

        # Step 4: Final Stage - Solve for X using H = Hf + x*Hfg 
        # Calculation: x = (H2 - Hf_p1) / Hfg_p1
        x = (h2 - hf_p1) / hfg_p1

        return {
            'p1': p1_kpa, 't1': t1_c, 'p2': p2_kpa, 't2': t2_c,
            'hf': hf_p1, 'hfg': hfg_p1, 'tsat1': tsat_p1,
            'tsat2': tsat_p2, 'h2': h2, 's2': s2, 'v2': v2,
            'state': state, 'x': x
        }
    except Exception as e:
        print(f"Error in {case_name}: {e}")
        return None

# --- VISUALIZATION & REPORTING ---
def generate_outputs(data, case_name):
    """Generates detailed TXT reports and multiple PNG graphs."""
    folder = f"Output_{case_name}"
    os.makedirs(folder, exist_ok=True)

    # 1. GENERATE TXT REPORT
    with open(f"{folder}/Report_{case_name}.txt", 'w') as f:
        f.write(f"THROTTLING CALORIMETER REPORT - {case_name}\n")
        f.write(f"Generated on: {datetime.datetime.now()}\n")
        f.write("-" * 50 + "\n")
        f.write(f"INPUTS:\n- P1: {data['p1']} kPa\n- T1: {data['t1']} C\n")
        f.write(f"- P2: {data['p2']} kPa\n- T2: {data['t2']} C\n\n")
        f.write(f"STEAM TABLE LOOKUPS (CoolProp Engine):\n")
        f.write(f"- Hf @ P1: {data['hf']:.2f} kJ/kg\n")
        f.write(f"- Hfg @ P1: {data['hfg']:.2f} kJ/kg\n")
        f.write(f"- Tsat @ P2: {data['tsat2']:.2f} C\n")
        f.write(f"- Total Enthalpy (H) @ P2: {data['h2']:.2f} kJ/kg\n\n")
        f.write(f"ANALYSIS:\n- Calculated State: {data['state']}\n")
        f.write(f"- SOLUTION STEPS:\n  H = Hf + x*Hfg\n  {data['h2']:.2f} = {data['hf']:.2f} + x*({data['hfg']:.2f})\n")
        f.write(f"- Dryness Fraction (X): {data['x']:.4f}\n")
        f.write("-" * 50 + "\n")

    # 2. GENERATE GRAPHS
    # Plot 1: T-H Diagram
    plt.figure(figsize=(8, 5))
    plt.plot([data['h2'], data['h2']], [data['tsat1'], data['t2']], 'ro-', label='Isenthalpic Path (H1=H2)')
    plt.title(f"T-H Diagram: {case_name}")
    plt.xlabel("Enthalpy (kJ/kg)"), plt.ylabel("Temperature (C)")
    plt.grid(True), plt.legend()
    plt.savefig(f"{folder}/T-H_Diagram.png")
    plt.close()

    # Plot 2: P-V Diagram
    plt.figure(figsize=(8, 5))
    plt.scatter([data['v2']], [data['p2']], color='blue', s=100, label='Final State (P2, v2)')
    plt.title(f"P-V Point: {case_name}")
    plt.xlabel("Specific Volume (m3/kg)"), plt.ylabel("Pressure (kPa)")
    plt.grid(True), plt.legend()
    plt.savefig(f"{folder}/P-V_Diagram.png")
    plt.close()

# --- MAIN EXECUTION ---
def main():
    print("Welcome to the Enhanced Throttling Calorimeter Suite")
    mode = input("Select Mode:\n1. Manual Input\n2. Simulated Random Inputs (3 Cases)\nChoice: ")

    if mode == '1':
        p1 = get_input("Enter P1 (kPa)")
        t1 = get_input("Enter T1 (C)")
        p2 = get_input("Enter P2 (kPa)")
        t2 = get_input("Enter T2 (C)")
        results = analyze_throttling(p1, t1, p2, t2, "Manual_Entry")
        if results: 
            generate_outputs(results, "Manual_Entry")
            print("✅ Report and Graphs generated in 'Output_Manual_Entry' folder.")

    else:
        print("\n--- Generating 3 Simulated Cases ---")
        for i in range(1, 4):
            # Simulation logic to find optimal conditions
            s_p1 = random.randint(600, 1000)
            s_t1 = 170 # Proximal saturation
            s_p2 = random.randint(100, 201)
            s_t2 = random.randint(110, 160) # Aiming for superheat
            
            results = analyze_throttling(s_p1, s_t1, s_p2, s_t2, f"Simulated_Case_{i}")
            if results:
                generate_outputs(results, f"Simulated_Case_{i}")
                print(f"✅ Case {i}: State={results['state']}, X={results['x']:.4f}")

if __name__ == "__main__":
    main()