import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use('Agg') # Stable backend for report generation
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
    Computes thermodynamic properties and determines suitability.
    """
    p1_pa, p2_pa = p1_kpa * 1000.0, p2_kpa * 1000.0
    t2_k = t2_c + 273.15

    try:
        # [cite_start]Step 1: Before Throttling - Lookups at P1 [cite: 1, 4, 5]
        hf_p1 = CP.PropsSI('H', 'P', p1_pa, 'Q', 0, FLUID) / 1000.0
        hg_p1 = CP.PropsSI('H', 'P', p1_pa, 'Q', 1, FLUID) / 1000.0
        hfg_p1 = hg_p1 - hf_p1
        tsat_p1 = CP.PropsSI('T', 'P', p1_pa, 'Q', 0, FLUID) - 273.15

        # [cite_start]Step 2: After Throttling - Lookups at P2 [cite: 8, 9]
        tsat_p2 = CP.PropsSI('T', 'P', p2_pa, 'Q', 0, FLUID) - 273.15
        h2 = CP.PropsSI('H', 'P', p2_pa, 'T', t2_k, FLUID) / 1000.0
        
        # [cite_start]Step 3: Conclude Steam State & Suitability [cite: 7]
        x = None
        verdict = ""
        is_suitable = False
        
        if t2_c > tsat_p2 + 0.5:
            state = "Superheated steam"
            verdict = "SUITABLE: The outlet steam is superheated, allowing for an accurate H2 lookup."  # [cite: 7]
            is_suitable = True
            # Solve for X: x = (H - Hf) / Hfg [cite: 10]
            x = (h2 - hf_p1) / hfg_p1
        elif t2_c < tsat_p2 - 0.5:
            state = "Wet steam"
            verdict = "NOT SUITABLE: Steam is still wet after throttling. Dryness fraction cannot be determined."  # [cite: 7]
        else:
            state = "Saturated steam"
            verdict = "MARGINAL: Steam is at saturation point. Accuracy is limited."  # [cite: 7]

        return {
            'p1': p1_kpa, 't1': t1_c, 'p2': p2_kpa, 't2': t2_c,
            'hf': hf_p1, 'hfg': hfg_p1, 'tsat1': tsat_p1,
            'tsat2': tsat_p2, 'h2': h2, 'state': state, 
            'x': x, 'verdict': verdict, 'is_suitable': is_suitable
        }
    except Exception as e:
        print(f"Error in {case_name}: {e}")
        return None

# --- VISUALIZATION & REPORTING ---
def generate_outputs(data, case_name):
    folder = f"Output_{case_name}"
    os.makedirs(folder, exist_ok=True)

    # 1. GENERATE TXT REPORT WITH CALCULATION STEPS
    with open(f"{folder}/Report_{case_name}.txt", 'w') as f:
        f.write(f"--- THROTTLING CALORIMETER ANALYSIS: {case_name} ---\n")
        f.write(f"Generated: {datetime.datetime.now()}\n")
        f.write("="*65 + "\n")
        f.write(f"EXPERIMENTAL INPUTS:\n")
        f.write(f"- Inlet Pressure (P1): {data['p1']} kPa\n")
        f.write(f"- Outlet Pressure (P2): {data['p2']} kPa\n")
        f.write(f"- Outlet Temp (T2): {data['t2']} C\n\n")
        
        f.write(f"THERMODYNAMIC LOOKUPS (Table A-5 Simulation):\n")
        f.write(f"- Hf @ P1: {data['hf']:.2f} kJ/kg\n")
        f.write(f"- Hfg @ P1: {data['hfg']:.2f} kJ/kg\n")
        f.write(f"- Tsat @ P2: {data['tsat2']:.2f} C\n")
        f.write(f"- Final Enthalpy (H2) @ P2: {data['h2']:.2f} kJ/kg\n\n")
        
        f.write(f"STEP-BY-STEP CALCULATION:\n")
        f.write(f"1. Isenthalpic Assumption: H1 = H2 = {data['h2']:.2f} kJ/kg\n")
        f.write(f"2. Mixture Formula: H1 = Hf + x * Hfg\n")
        
        if data['is_suitable']:
            f.write(f"3. Solving for x: x = (H2 - Hf) / Hfg\n")
            f.write(f"   x = ({data['h2']:.2f} - {data['hf']:.2f}) / {data['hfg']:.2f}\n")
            f.write(f"   RESULT: x = {data['x']:.4f}\n")
        else:
            f.write(f"3. Solving for x: FAILED\n")
            f.write(f"   REASON: Steam state is {data['state']}. Cannot uniquely determine H2.\n")
            
        f.write(f"\nFINAL VERDICT: {data['verdict']}\n")
        f.write("="*65 + "\n")

    # 2. GENERATE GRAPH 1: T-h Diagram (Showing Isenthalpic Path)
    plt.figure(figsize=(8, 5))
    plt.plot([data['h2'], data['h2']], [data['tsat1'], data['t2']], 'ro-', linewidth=2, label='Throttling Path (H=const)')
    plt.title(f"T-h Diagram: {case_name}")
    plt.xlabel("Enthalpy (kJ/kg)"), plt.ylabel("Temperature (C)")
    plt.grid(True, linestyle='--', alpha=0.6), plt.legend()
    plt.savefig(f"{folder}/T-h_Diagram.png")
    plt.close()

    # 3. GENERATE GRAPH 2: P-T Diagram (Showing Saturation Curve)
    plt.figure(figsize=(8, 5))
    # Generate saturation curve for context
    T_range = np.linspace(273.16, CP.PropsSI('Tcrit', FLUID)-2, 100)
    P_sat = [CP.PropsSI('P', 'T', T, 'Q', 0, FLUID)/1000 for T in T_range]
    plt.plot([T-273.15 for T in T_range], P_sat, 'b-', label='Saturation Curve')
    plt.scatter([data['tsat1'], data['t2']], [data['p1'], data['p2']], color='red', label='Inlet/Outlet States')
    plt.yscale('log'), plt.title(f"P-T Diagram: {case_name}")
    plt.xlabel("Temperature (C)"), plt.ylabel("Pressure (kPa)")
    plt.grid(True, which='both', alpha=0.3), plt.legend()
    plt.savefig(f"{folder}/P-T_Diagram.png")
    plt.close()

# --- MAIN EXECUTION ---
def main():
    print("Welcome to the Professional Throttling Calorimeter Suite")
    mode = input("1. Manual Entry\n2. 3-Case Automated Simulation\nChoice: ")

    if mode == '1':
        p1 = get_input("Enter P1 (kPa)")
        t1 = get_input("Enter T1 (C)") # Used for diagram plotting context
        p2 = get_input("Enter P2 (kPa)")
        t2 = get_input("Enter T2 (C)")
        results = analyze_throttling(p1, t1, p2, t2, "Manual_Analysis")
        if results: 
            generate_outputs(results, "Manual_Analysis")
            print("✅ Report and 2 Diagrams saved in 'Output_Manual_Analysis' folder.")
    else:
        for i in range(1, 4):
            s_p1, s_p2 = random.randint(600, 1000), random.randint(100, 200)
            s_t2 = random.randint(110, 160)
            res = analyze_throttling(s_p1, 180, s_p2, s_t2, f"Sim_Case_{i}")
            if res: generate_outputs(res, f"Sim_Case_{i}")
        print("✅ 3 Case Reports and Diagrams generated in separate folders.")

if __name__ == "__main__":
    main()