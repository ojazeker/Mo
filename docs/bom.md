# Bill of Materials

_Last updated Apr 20, 2026_

| ID | Component | Notes | Part used | Verdict |
|---|---|---|---|---|
| 01 | 58mm Thermal Printer | Pick one with TTL support. Many options available, mostly from China. | GOOJPRT QR204 
| 02 | Raspberry Pi Zero W2 | 512MB RAM, runs great. Card data needs to be optimised — you cannot scan massive database files on it. | Pi Zero W2 
| 03 | PD Trigger | Use one where the voltage can be locked. Many triggers support multiple outputs. 
| 04 | Buck Down Converter | Fixed 5A converter — overkill for this project, form factor can be smaller. 
| 05 | Power Bank | Must support PD. Use a powerful one (65W recommended). | Belkin BoostCharge Pro 20k 
| 06 | Mini USB → Micro USB cable | Printer supports USB and Serial. USB is much faster (Serial tops out at 9600 baud). You want a Micro→Mini USB cable with angled headers, ~10cm. Hard to find — may require custom soldering. 
| 07 | Case | UG Boulder 133+ — split down the middle gives easy access to the printer bottom. Matches EDH deck boxes nicely. | 133+ Return to Earth 
| 08 | PCB | Any 2.54mm spaced PCB will do. A 2×8cm board is plenty — trim to fit. A Raspberry Pi Zero shield would be a nicer solution.
| 10 | 2-state switch | Simple dip switch works. A switch with a built-in LED status indicator would be nicer.
| 11 | MicroSD Card | Anything over a few GB works — pick a fast one. | SanDisk MicroSDHC Extreme Pro 32GB 90MB/s

---

## Extra Notes

- A **TS101 by Miniware** soldering iron works great for this build and can be powered directly from the power bank — handier than expected.
- Use **thin, flexible wire** — thick wire is very hard to fit inside the case.
- The hole in the case was made using a **Dremel with a diamond disc**.

most recent version of bom: https://docs.google.com/document/d/1q88H3A5H7vmjqbWVD-xpVFSqKajT9pj9gsuM4C6IBSg/edit?usp=sharing