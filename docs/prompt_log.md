# AI Fitness Platform - LLM Prompt Generation Log

This document records 5 distinct test runs evaluating the prompt template and `Plan` schema across varying fitness goals, experience levels, equipment access, and physical constraints.

---

## Test Case 1: Beginner Fat Loss (Home Workout)
* **Goal**: Fat Loss & Cardio Endurance
* **Level**: Beginner
* **Equipment**: Dumbbells & Bodyweight
* **Frequency**: 3 days/week, 4 weeks
* **Limitations**: None
* **Sample Validated Output**:
```json
{
  "goal": "Fat Loss & Cardio Endurance",
  "level": "Beginner",
  "weeks": [
    {
      "number": 1,
      "days": [
        {
          "name": "Monday",
          "focus": "Full Body Circuit",
          "exercises": [
            {"name": "Goblet Squats", "sets": 3, "reps": 12, "rest_sec": 45, "notes": "Controlled descent"},
            {"name": "Dumbbell Floor Press", "sets": 3, "reps": 10, "rest_sec": 45, "notes": "Keep elbows at 45 degrees"},
            {"name": "Mountain Climbers", "sets": 3, "reps": 20, "rest_sec": 30, "notes": "Maintain tight core"}
          ]
        },
        {
          "name": "Wednesday",
          "focus": "Lower Body & Core",
          "exercises": [
            {"name": "Dumbbell Romanian Deadlifts", "sets": 3, "reps": 10, "rest_sec": 60, "notes": "Hinge at the hips"},
            {"name": "Reverse Lunges", "sets": 3, "reps": 10, "rest_sec": 45, "notes": "10 per leg"},
            {"name": "Plank", "sets": 3, "reps": 30, "rest_sec": 30, "notes": "Hold for 30 seconds"}
          ]
        },
        {
          "name": "Friday",
          "focus": "Upper Body & Conditioning",
          "exercises": [
            {"name": "Dumbbell Bent-Over Rows", "sets": 3, "reps": 12, "rest_sec": 45, "notes": "Squeeze scapula"},
            {"name": "Push-Ups (or Knee Push-ups)", "sets": 3, "reps": 8, "rest_sec": 60, "notes": "Chest to floor"},
            {"name": "Jumping Jacks", "sets": 3, "reps": 25, "rest_sec": 30, "notes": "Aerobic pace"}
          ]
        }
      ]
    }
  ]
}
```

---

## Test Case 2: Advanced Muscle Hypertrophy (Gym Access)
* **Goal**: Hypertrophy (Muscle Gain)
* **Level**: Advanced
* **Equipment**: Full Commercial Gym (Barbells, Cables, Dumbbells)
* **Frequency**: 5 days/week, 8 weeks
* **Limitations**: None
* **Sample Validated Output**:
```json
{
  "goal": "Hypertrophy",
  "level": "Advanced",
  "weeks": [
    {
      "number": 1,
      "days": [
        {
          "name": "Monday",
          "focus": "Chest & Triceps Hypertrophy",
          "exercises": [
            {"name": "Barbell Bench Press", "sets": 4, "reps": 8, "rest_sec": 120, "notes": "RPE 8, 2s eccentric"},
            {"name": "Incline Dumbbell Press", "sets": 4, "reps": 10, "rest_sec": 90, "notes": "Deep chest stretch"},
            {"name": "Cable Chest Flyes", "sets": 3, "reps": 15, "rest_sec": 60, "notes": "Squeeze at peak contraction"},
            {"name": "Tricep Rope Pushdowns", "sets": 4, "reps": 12, "rest_sec": 60, "notes": "Full lockout"}
          ]
        }
      ]
    }
  ]
}
```

---

## Test Case 3: Joint-Friendly Injury Adaptation
* **Goal**: Strength & Muscular Tone
* **Level**: Intermediate
* **Equipment**: Barbells, Dumbbells, Cables
* **Frequency**: 4 days/week, 6 weeks
* **Limitations**: "Lower back stiffness, avoid heavy spinal loading like deadlifts"
* **Adaptation Verified**: Model replaced heavy barbell deadlifts with chest-supported dumbbell rows and hip-thrusts to spare the lumbar spine.

---

## Test Case 4: Minimalist Calisthenics
* **Goal**: Functional Athleticism & Bodyweight Mastery
* **Level**: Intermediate
* **Equipment**: Pull-up Bar & Dip Station
* **Frequency**: 3 days/week, 4 weeks
* **Limitations**: None
* **Adaptation Verified**: Strict calisthenics progressions (Pull-ups, Dips, Pike Push-ups, Pistol Squats) adhering to strict rep and rest constraints.

---

## Test Case 5: Senior Mobility & Balance
* **Goal**: Active Longevity & Fall Prevention
* **Level**: Beginner
* **Equipment**: Resistance Bands & Chair
* **Frequency**: 2 days/week, 2 weeks
* **Limitations**: Knee arthritis
* **Adaptation Verified**: Low-impact isometric holds, sit-to-stands, banded lateral walks, and ankle mobility drills with low set/rep strain.
