from __future__ import annotations

import pandas as pd
import streamlit as st

from database.database import SessionLocal
from database.repository import ensure_astronaut
from database.models import NutritionRecord
from database.repository import get_nutrition_records


def render_nutrition():
    st.subheader("Nutrition Tracking")
    session = SessionLocal()
    try:
        with st.form("nutrition_form"):
            meal_name = st.text_input("Meal or food item")
            calories = st.number_input("Calories", min_value=0.0, step=10.0)
            protein = st.number_input("Protein (g)", min_value=0.0, step=1.0)
            carbs = st.number_input("Carbs (g)", min_value=0.0, step=1.0)
            fats = st.number_input("Fats (g)", min_value=0.0, step=1.0)
            hydration = st.number_input("Hydration (L)", min_value=0.0, step=0.1)
            estimated = st.checkbox("Values are estimated")
            submitted = st.form_submit_button("Save nutrition record")

        if submitted and meal_name:
            record = NutritionRecord(
                astronaut_id=ensure_astronaut(session).id,
                meal_name=meal_name,
                calories=float(calories) if calories else None,
                protein_g=float(protein) if protein else None,
                carbs_g=float(carbs) if carbs else None,
                fats_g=float(fats) if fats else None,
                hydration_liters=float(hydration) if hydration else None,
                estimated=bool(estimated),
            )
            session.add(record)
            session.commit()
            st.success("Nutrition record saved.")

        rows = get_nutrition_records(session)
        if rows:
            df = pd.DataFrame([
                {
                    "Meal": item.meal_name,
                    "Calories": item.calories,
                    "Protein (g)": item.protein_g,
                    "Carbs (g)": item.carbs_g,
                    "Hydration (L)": item.hydration_liters,
                    "Estimated": item.estimated,
                    "Timestamp": item.meal_time.strftime("%Y-%m-%d %H:%M")
                } for item in rows
            ])
            st.dataframe(df, width="stretch")
        else:
            st.info("No nutrition records available yet.")
    finally:
        session.close()
