import CoolProp.CoolProp as CP
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server/terminal stability
import matplotlib.pyplot as plt
import numpy as np
import sys
import datetime
import os

# --- CONFIGURATION ---
FLUID = 'Water'

def get_input(prompt, min_val=0.01):
    """Improved prompting with validation and range checking."""
    while True:
        try:
            val = float(input(f"➤ {prompt}: ").strip())
            if val < min_val:
                print(f"  ⚠️  Value must be greater than {min_val}. Please re-enter.")
                continue
            return val
        except ValueError:
            print("  ⚠️  Invalid input. Please enter a numerical value.")

# --- THERMODYNAMIC ENGINE ---
def analyze_steam(p1_kpa, t1_c, p2_kpa, t2_c):
    """Performs all lookups and calculations based on project requirements."""
    p1_pa, p2_pa = p1_kpa * 1000.0, p2_kpa * 1000.0
    t2_k = t2_c + 273.15

    try:
        # Properties Before Throttling (P1) 
        hf_p1 = CP.PropsSI('H', 'P', p1_pa, 'Q', 0, FLUID) / 1000.0  # [cite: 4]
        hfg_p1 = (CP.PropsSI('H', 'P', p1_pa, 'Q', 1, FLUID) - (hf_p1 * 1000.0)) / 1000.0  # [cite: 5]
        tsat_p1 = CP.PropsSI('T', 'P', p1_pa, 'Q', 0, FLUID) - 273.15

        # Properties After Throttling (P2) [cite: 8, 9]
        tsat_p2 = CP.PropsSI('T', 'P', p2_pa, 'Q', 0, FLUID) - 273.15  # 
        h2 = CP.PropsSI('H', 'P', p2_pa, 'T', t2_k, FLUID) / 1000.0  # 
        s2 = CP.PropsSI('S', 'P', p2_pa, 'T', t2_k, FLUID) / 1000.0
        v2 = 1.0 / CP.PropsSI('D', 'P', p2_pa, 'T', t2_k, FLUID)

        # State Determination [cite: 7]
        if t2_c > tsat_p2 + 0.5:
            state = "Superheated"
        elif t2_c < tsat_p2 - 0.5:
            state = "Wet"
        else:
            state = "Saturated"

        # Dryness Fraction Calculation 
        # Formula: H1 = H2 -> Hf + x*Hfg = H2
        x = (h2 - hf_p1) / hfg_p1  # 

        return {
            'hf': hf_p1, 'hfg': hfg_p1, 'tsat1': tsat_p1,
            'tsat2': tsat_p2, 'h2': h2, 's2': s2, 'v2': v2,
            'state': state, 'x': x
        }
    except Exception as e:
        print(f"❌ Calculation Error: {e}")
        return None

# --- INDIVIDUAL PLOTTING FUNCTIONS ---
def save_plots(p1, p2, t2, data):
    """Generates and saves each graph as a separate file."""
    plt.style.use('seaborn-v0_8-muted')
    os.makedirs('plots', exist_ok=True)
    
    # 1. T-H Diagram (The Isenthalpic Path)
    
    plt.figure(figsize=(8, 6))
    plt.plot([data['h2'], data['h2']], [data['tsat1'], t2], 'ro-', linewidth=3, label='Throttling Path (H=const)')
    plt.title("Temperature-Enthalpy (T-H) Diagram")
    plt.xlabel("Enthalpy (kJ/kg)"), plt.ylabel("Temperature (°C)")
    plt.grid(True, linestyle='--', alpha=0.7), plt.legend()
    plt.savefig('plots/1_TH_Diagram.png', dpi=300)
    plt.close()

    # 2. P-T Diagram (Phase Boundary)
    

    plt.figure(figsize=(8, 6))
    t_range = np.linspace(274, CP.PropsSI('Tcrit', FLUID)-2, 100)
    p_sat = [CP.PropsSI('P', 'T', t, 'Q', 0, FLUID)/1000 for t in t_range]
    plt.plot([t-273.15 for t in t_range], p_sat, 'b-', label='Saturation Line')
    plt.scatter([data['tsat1'], t2], [p1, p2], color='red', zorder=5, label='Inlet/Outlet States')
    plt.yscale('log'), plt.title("Pressure-Temperature (P-T) Phase Diagram")
    plt.xlabel("Temperature (°C)"), plt.ylabel("Pressure (kPa - Log Scale)")
    plt.grid(True, which="both", linestyle='--', alpha=0.5), plt.legend()
    plt.savefig('plots/2_PT_Diagram.png', dpi=300)
    plt.close()

    # 3. T-s Diagram (Entropy visualization)
    
    plt.figure(figsize=(8, 6))
    plt.scatter([data['s2']], [t2], color='green', s=100, label=f"Final State (s={data['s2']:.2f})")
    plt.title("Temperature-Entropy (T-s) Position")
    plt.xlabel("Entropy (kJ/kg·K)"), plt.ylabel("Temperature (°C)")
    plt.grid(True), plt.legend()
    plt.savefig('plots/3_TS_Point.png', dpi=300)
    plt.close()

# --- IMPROVED REPORT GENERATOR ---
def create_scientific_report(p1, t1, p2, t2, d):
    """Generates a detailed scientific report."""
    filename = f"Throttling_Report_{datetime.datetime.now().strftime('%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write("==========================================================\n")
        f.write("     THERMODYNAMIC ANALYSIS: THROTTLING CALORIMETER\n")
        f.write("==========================================================\n")
        f.write(f"Timestamp: {datetime.datetime.now()}\n")
        f.write(f"Working Fluid: {FLUID}\n\n")

        f.write("1. EXPERIMENTAL INPUTS\n")
        f.write(f"   Inlet Pressure (P1):  {p1:>10} kPa [cite: 2]\n")
        f.write(f"   Inlet Temp (T1):      {t1:>10} °C  [cite: 3]\n")
        f.write(f"   Outlet Pressure (P2): {p2:>10} kPa [cite: 6]\n")
        f.write(f"   Outlet Temp (T2):     {t2:>10} °C  [cite: 7]\n\n")

        f.write("2. STEAM TABLE PROPERTIES (CoolProp Engine)\n")
        f.write(f"   Sat. Liquid Enthalpy (hf@P1): {d['hf']:>8.2f} kJ/kg [cite: 4]\n")
        f.write(f"   Latent Heat (hfg@P1):        {d['hfg']:>8.2f} kJ/kg [cite: 5]\n")
        f.write(f"   Sat. Temp (Tsat@P2):         {d['tsat2']:>8.2f} °C  \n")
        f.write(f"   Final Enthalpy (H2):         {d['h2']:>8.2f} kJ/kg \n\n")

        f.write("3. ANALYSIS RESULTS\n")
        f.write(f"   Post-Throttling State: {d['state'].upper()} [cite: 7]\n")
        f.write(f"   Dryness Fraction (x):  {d['x']:>10.4f} \n\n")

        f.write("4. GOVERNING EQUATIONS\n")
        f.write("   Isenthalpic Process: H1 = H2\n")
        f.write("   Mixture Equation:    H1 = Hf + x * Hfg\n")
        f.write("   Solved for x:        x = (H2 - Hf) / Hfg\n")
        f.write("==========================================================\n")
    return filename

# --- MAIN EXECUTION ---
def main():
    print("--- 🔬 STARTING THROTTLING CALORIMETER SIMULATION ---")
    p1 = get_input("Enter Inlet Pressure P1 (kPa)")
    t1 = get_input("Enter Measured Inlet Temp T1 (°C)")
    p2 = get_input("Enter Outlet Pressure P2 (kPa)")
    t2 = get_input("Enter Measured Outlet Temp T2 (°C)")

    results = analyze_steam(p1, t1, p2, t2)
    
    if results:
        report_name = create_scientific_report(p1, t1, p2, t2, results)
        save_plots(p1, p2, t2, results)
        
        print(f"\n✅ ANALYSIS COMPLETE")
        print(f"📄 Scientific Report: {report_name}")
        print(f"📈 Graphs saved in '/plots' folder: TH_Diagram.png, PT_Diagram.png, TS_Point.png")
        print(f"💡 Calculated Dryness Fraction: {results['x']:.4f}")

if __name__ == "__main__":
    main()