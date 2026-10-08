"""knowledge_base.py — Structured agricultural knowledge base for Tomato and Potato crops.

Provides authoritative, conservative, non-hallucinatory information on:
- Tomato Early Blight (Alternaria solani)
- Tomato Late Blight (Phytophthora infestans)
- Potato Early Blight (Alternaria solani)
- Potato Late Blight (Phytophthora infestans)
- Healthy Tomato & Potato maintenance

Covers symptoms, favorable conditions, transmission, prevention, cultural practices,
general treatment classes, and extension thresholds.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "Tomato___Early_blight": {
        "crop": "Tomato",
        "disease": "Early Blight",
        "pathogen": "Alternaria solani (Fungus)",
        "overview": (
            "Tomato Early Blight is a common fungal disease caused by *Alternaria solani*. "
            "It primarily attacks the older, lower leaves first and gradually progresses upward "
            "through the plant canopy, causing defoliation, sunscald on fruits, and reduced yield."
        ),
        "symptoms": [
            "Concentric brown-to-black ringed lesions forming a characteristic 'target-board' or 'bullseye' pattern.",
            "Yellow halo (chlorosis) frequently surrounding older dark lesions.",
            "Symptoms begin on mature lower foliage near the soil level.",
            "Progressive yellowing, browning, and premature dropping of infected leaves.",
            "Dark, sunken, leathery lesions near the stem end of tomato fruit in severe cases.",
        ],
        "causes_and_favorable_conditions": [
            "Favorable temperatures: Moderate to warm weather (24°C – 29°C / 75°F – 85°F).",
            "Prolonged leaf wetness caused by rainfall, heavy dew, or overhead sprinkler watering.",
            "Dense canopy with poor air circulation that slows foliage drying.",
            "Overwintering fungal spores in undecomposed crop residue and solanaceous weeds (e.g., nightshade).",
        ],
        "transmission": [
            "Spores (*conidia*) are splashed by raindrops or overhead irrigation onto lower leaves.",
            "Spores can be carried between fields by wind currents.",
            "Survival on contaminated farming equipment, stakes, cages, and overwintering garden debris.",
        ],
        "prevention": [
            "Practice 3-to-4 year crop rotation with non-solanaceous crops (avoid planting after potatoes, peppers, or eggplants).",
            "Use drip or furrow irrigation rather than overhead watering to keep foliage dry.",
            "Apply clean organic mulch (straw or plastic) around the base of plants to create a barrier preventing soil splash.",
            "Prune bottom 12–18 inches of leaves once plants are established to eliminate contact with soil.",
            "Stake or cage plants to promote upright growth and maximize airflow.",
            "Thoroughly clean up and compost or dispose of all solanaceous plant residue at the end of the harvest season.",
        ],
        "treatment_guidance": {
            "Mild": (
                "For mild or localized spotting on lower leaves, immediately pinch off and destroy infected leaves. "
                "Ensure mulch is in place and eliminate overhead watering. Chemical sprays are generally not required "
                "at this early stage if sanitation is promptly executed."
            ),
            "Moderate": (
                "Prune blighted foliage and clear fallen debris. If weather conditions remain wet or humid, consider applying "
                "a locally approved protective contact fungicide (such as copper-based formulations or certified bio-fungicides) "
                "to safeguard uninfected upper leaves. Always follow the official product label."
            ),
            "Severe": (
                "Remove severely diseased branches without stripping the main stem. Consult your local agricultural "
                "extension officer for registered curative/therapeutic fungicides suitable for your region. "
                "Do not compost heavily diseased plant matter in home compost piles."
            ),
        },
        "when_to_seek_advice": (
            "Contact your local agricultural extension service or certified crop advisor if blight spreads rapidly "
            "into the upper third of the canopy despite cultural pruning, if lesions appear on green fruits, "
            "or if standard protective sprays fail to arrest development."
        ),
    },

    "Potato___Early_blight": {
        "crop": "Potato",
        "disease": "Early Blight",
        "pathogen": "Alternaria solani (Fungus)",
        "overview": (
            "Potato Early Blight is caused by *Alternaria solani*. Although called 'early', it typically appears "
            "mid-to-late season as vines mature and tuber bulk begins. It causes premature foliage loss and can "
            "subsequently infect potato tubers through harvest wounds, leading to dry rot during storage."
        ),
        "symptoms": [
            "Small, dark brown-to-black angular spots on older, lower foliage.",
            "Concentric concentric ridges inside spots giving a 'target-board' or 'bullseye' appearance.",
            "Lesions bounded by leaf veins, creating an angular look.",
            "Foliage yellowing and premature leaf senescence/drop.",
            "Tubers show brown to black, sunken, corky dry rot lesions with purplish margins if infected during harvest.",
        ],
        "causes_and_favorable_conditions": [
            "Alternating periods of wet and dry weather with warm temperatures (20°C – 28°C / 68°F – 82°F).",
            "Plant stress caused by poor nutrition (especially nitrogen deficiency), drought, or heavy tuber bulking.",
            "Frequent sprinkler irrigation or prolonged canopy wetness.",
            "Fungal survival in old potato vine residue or volunteer potato plants.",
        ],
        "transmission": [
            "Conidia spores transported by wind and splashing rain.",
            "Infection of tubers occurs primarily during harvest when tubers come into direct contact with blighted vines or spores in the soil.",
        ],
        "prevention": [
            "Rotate fields with non-solanaceous crops (grasses, corn, legumes) for at least 3 years.",
            "Maintain balanced plant nutrition—avoid nitrogen deficiency during tuber bulking.",
            "Irrigate early in the morning so the canopy dries quickly before nightfall.",
            "Destroy volunteer potato plants and nightshade weeds in and around the field.",
            "Allow potato skins to fully mature and set before harvest; avoid harvesting during wet soil conditions.",
            "Clean and sanitize tuber storage facilities and equipment thoroughly.",
        ],
        "treatment_guidance": {
            "Mild": (
                "Scout the field regularly. Remove scattered diseased lower foliage if feasible on small plots. "
                "Ensure plants are well-watered at the roots and receive balanced nitrogen and potassium."
            ),
            "Moderate": (
                "Clear blighted plant debris. Where warm and moist weather persists, consider applying locally registered "
                "protective fungicides (such as copper-based formulations or preventive protectants). Follow regional extension advice."
            ),
            "Severe": (
                "Intensive management is required to avoid premature vine death and tuber contamination. Consult your local "
                "agronomy extension service for approved targeted fungicides and plan appropriate vine desiccation prior to digging."
            ),
        },
        "when_to_seek_advice": (
            "Consult local extension specialists if early blight causes rapid defoliation during the critical tuber bulking stage, "
            "or if symptoms appear on tubers in storage."
        ),
    },

    "Tomato___Late_blight": {
        "crop": "Tomato",
        "disease": "Late Blight",
        "pathogen": "Phytophthora infestans (Oomycete / Water Mold)",
        "overview": (
            "Tomato Late Blight is a devastating, highly contagious plant disease caused by the oomycete *Phytophthora infestans*. "
            "It can destroy entire tomato fields within days under cool, wet, and overcast weather. It affects leaves, stems, "
            "and green or ripe fruit."
        ),
        "symptoms": [
            "Large, irregularly shaped, water-soaked, dark green to purplish-black lesions on leaves.",
            "Delicate white cottony/fuzzy mold sporulation on the underside of leaves during high humidity or morning dew.",
            "Dark brown to black lesions on petioles and main stems that cause stems to collapse.",
            "Large, firm, greasy brown-to-bronze leathery patches on green and ripe tomato fruits.",
            "Rapid plant collapse giving a 'frost-damaged' or burnt appearance across the canopy.",
        ],
        "causes_and_favorable_conditions": [
            "Cool, wet, cloudy, and humid weather (15°C – 22°C / 60°F – 72°F) with relative humidity above 90%.",
            "Prolonged leaf wetness (> 10–12 consecutive hours).",
            "Nearby infected potato cull piles, volunteer plants, or neighboring tomato fields.",
        ],
        "transmission": [
            "Microscopic spores (*sporangia*) are easily carried on the wind for miles.",
            "Swimming spores (*zoospores*) spread rapidly across wet leaf surfaces.",
            "Contaminated transplants and infected seed tubers.",
        ],
        "prevention": [
            "Plant only certified disease-free transplants or seed.",
            "Select late-blight resistant or tolerant tomato varieties where available.",
            "Maximize plant spacing and stake plants to ensure rapid leaf drying.",
            "Avoid overhead irrigation; water strictly at ground level.",
            "Inspect plants every 2–3 days during cool, damp weather.",
            "Eliminate nearby potato cull piles and solanaceous weeds.",
        ],
        "treatment_guidance": {
            "Mild": (
                "Late blight is an urgent plant health emergency. If isolated lesions are confirmed, immediately prune the affected leaves "
                "or pull the single infected plant, seal it in plastic, and dispose of it away from the garden. "
                "Apply locally registered preventive protective fungicides (such as copper compounds) to all healthy neighboring plants."
            ),
            "Moderate": (
                "Aggressive disease suppression is necessary. Prune infected stems, stop all overhead watering, and apply locally "
                "approved systemic/translaminar late blight fungicides according to your agricultural extension service guidelines."
            ),
            "Severe": (
                "Extensive late blight rarely responds to curative sprays. Heavily diseased plants should be pulled up, bagged, "
                "and destroyed immediately to prevent airborne spores from wiping out remaining tomatoes and surrounding potato crops. "
                "Never compost late-blight infected plant material."
            ),
        },
        "when_to_seek_advice": (
            "Late blight outbreaks should be reported to your local agricultural extension service immediately. "
            "Extension offices often track active late blight spore fronts and provide regional emergency spray alerts."
        ),
    },

    "Potato___Late_blight": {
        "crop": "Potato",
        "disease": "Late Blight",
        "pathogen": "Phytophthora infestans (Oomycete / Water Mold)",
        "overview": (
            "Potato Late Blight, caused by *Phytophthora infestans*, is the historic pathogen responsible for the Irish Potato Famine. "
            "It is one of the most destructive potato diseases worldwide, capable of killing lush potato vines within a week "
            "and causing catastrophic tuber rot in the ground and in storage."
        ),
        "symptoms": [
            "Water-soaked, dark green to brown-black irregular lesions that expand rapidly across leaves.",
            "Fine white fungal-like growth visible on the undersides of blighted leaves in humid or dewy mornings.",
            "Dark brown lesions girdling stems and leaf petioles.",
            "Infected tubers exhibit coppery-brown, dry, granular rot penetrating irregularly beneath the skin.",
            "Secondary bacterial soft rots often invade, turning rotting tubers into a foul-smelling slime.",
        ],
        "causes_and_favorable_conditions": [
            "Cool, foggy, wet weather (10°C – 20°C / 50°F – 68°F) accompanied by rainfall, fog, or heavy dew.",
            "Relative humidity consistently above 90% with wet leaf surfaces.",
            "Sprouting infected cull piles, volunteer potatoes, or uncertified seed tubers.",
        ],
        "transmission": [
            "Airborne sporangia can travel tens of miles on wind currents during overcast days.",
            "Rain washes sporangia from blighted foliage down into the soil ridges to infect tubers.",
            "Infected seed tubers sprout and launch early-season canopy epidemics.",
        ],
        "prevention": [
            "Plant exclusively certified disease-free seed potatoes.",
            "Destroy all potato cull piles (bury, feed to livestock, or freeze) before planting season.",
            "Hill/ridge soil generously over potato tubers to create a soil buffer against spore wash-down.",
            "Monitor regional late blight forecasting models and weather advisories.",
            "Avoid overhead irrigation, particularly late in the afternoon or evening.",
            "Before harvest, kill/desiccate vines at least 2–3 weeks ahead to ensure spores on foliage are dead before tubers are dug.",
        ],
        "treatment_guidance": {
            "Mild": (
                "Treat with urgent priority. Scout fields daily. Apply locally registered preventive barrier fungicides "
                "to healthy plants to block incoming spores. Remove isolated infected plants immediately if feasible."
            ),
            "Moderate": (
                "Immediate disease suppression is critical. Apply locally registered targeted fungicides (translaminar or systemic) "
                "recommended by regional extension services. Ensure high spray coverage under the canopy."
            ),
            "Severe": (
                "Critical emergency. If vine collapse is extensive, immediately desiccate or burn down vines to prevent spores "
                "from washing into tubers. Allow tubers to sit in the soil for 2–3 weeks before digging. Do not harvest wet."
            ),
        },
        "when_to_seek_advice": (
            "Immediately notify your local agricultural extension agent or commercial crop specialist. "
            "Late blight requires community-level monitoring and time-sensitive intervention."
        ),
    },

    "Healthy_Foliage": {
        "crop": "Tomato & Potato",
        "disease": "Healthy",
        "pathogen": "None (Non-diseased)",
        "overview": (
            "Healthy tomato and potato foliage is characterized by vibrant green coloration, uniform leaf texture, "
            "and absence of chlorosis (yellowing), necrotic lesions, water-soaking, or fungal sporulation. "
            "Maintaining plant vigor is the best defense against opportunistic blight infections."
        ),
        "symptoms": [
            "Consistent green coloration without brown or black necrotic spots.",
            "No yellow halos, concentric ring patterns, or water-soaked patches.",
            "Clean leaf undersides without white, fuzzy, or velvety mold growth.",
            "Firm, upright stems and vigorous vegetative growth.",
        ],
        "causes_and_favorable_conditions": [
            "Well-drained, fertile soil with balanced organic matter (pH 6.0–6.8).",
            "Consistent soil moisture via root-level irrigation.",
            "Full sunlight (6–8 hours daily).",
            "Good air movement through properly spaced plants.",
        ],
        "transmission": [
            "Not applicable. Foliage is healthy and disease-free."
        ],
        "prevention": [
            "Continue routine field scouting (inspect lower leaves and undersides 1–2 times weekly).",
            "Water exclusively at the base (drip irrigation, soaker hoses) to keep leaves dry.",
            "Apply 2–3 inches of mulch around plant bases to prevent soil splashing.",
            "Prune bottom suckers and lower tomato leaves up to 12 inches to improve airflow.",
            "Maintain balanced fertilization—excessive nitrogen produces lush, succulent growth that is more prone to disease.",
            "Practice multi-year crop rotation with non-nightshade species.",
        ],
        "treatment_guidance": {
            "None": (
                "No chemical spraying or pesticide treatment is recommended for healthy crops. "
                "Unnecessary chemical applications add expense, harm beneficial microorganisms and pollinators, "
                "and risk breeding chemical resistance. Focus entirely on preventative cultural management."
            ),
        },
        "when_to_seek_advice": (
            "Consult agricultural extension if you notice sudden widespread wilting, unusual leaf curling, "
            "or unexplained yellowing that does not match blight spotting."
        ),
    },
}

GENERAL_DISCLAIMER = (
    "Disclaimer: This agricultural guidance is for educational and advisory reference only. "
    "Always consult your local agricultural extension service, university research station, "
    "or certified crop advisor, and strictly adhere to official pesticide product labels and local regulations."
)
