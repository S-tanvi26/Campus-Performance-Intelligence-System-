import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
STUDENTS_FILE = BASE_DIR / "students.csv"
ATTENDANCE_FILE = BASE_DIR / "attendance.csv"
SCHOLARSHIP_FILE = BASE_DIR / "scholarships.json"
DATABASE_FILE = BASE_DIR / "student_hackathon.db"
REPORT_FILE = BASE_DIR / "report.json"
DEPARTMENT_CHART = BASE_DIR / "department_performance.png"
PERFORMANCE_CHART = BASE_DIR / "performance_distribution.png"


def load_data():
    """Load CSV and JSON source data."""
    students = pd.read_csv(STUDENTS_FILE)
    attendance = pd.read_csv(ATTENDANCE_FILE)

    with open(SCHOLARSHIP_FILE, "r", encoding="utf-8") as file:
        scholarships = json.load(file)

    return students, attendance, scholarships


def validate_data(students, attendance, scholarships):
    """Validate required columns and scholarship rule structure."""
    student_columns = {"student_id", "name", "department", "city", "marks"}
    attendance_columns = {"student_id", "attendance"}

    if not student_columns.issubset(students.columns):
        raise ValueError(f"students.csv is missing columns: {student_columns - set(students.columns)}")

    if not attendance_columns.issubset(attendance.columns):
        raise ValueError(f"attendance.csv is missing columns: {attendance_columns - set(attendance.columns)}")

    required_rule_fields = {
        "department", "bonus_marks", "minimum_marks", "minimum_attendance"
    }
    for rule in scholarships:
        if not required_rule_fields.issubset(rule):
            raise ValueError(
                f"Scholarship rule is missing: {required_rule_fields - set(rule)}"
            )

    if students["student_id"].duplicated().any():
        raise ValueError("Duplicate student_id values found in students.csv.")

    if attendance["student_id"].duplicated().any():
        raise ValueError("Duplicate student_id values found in attendance.csv.")


def inspect_data(students, scholarships):
    """Display basic dataset inspection."""
    print("\n--- TASK 1: DATA INSPECTION ---")
    print("Number of students:", len(students))
    print("Number of departments:", students["department"].nunique())
    print("Unique cities:", sorted(students["city"].dropna().unique().tolist()))
    print("\nFirst five student records:")
    print(students.head().to_string(index=False))
    print("\nScholarship rules:")
    print(json.dumps(scholarships, indent=4))


def merge_student_data(students, attendance):
    """Merge student information with attendance using student_id."""
    merged = students.merge(
        attendance,
        on="student_id",
        how="left",
        validate="one_to_one",
        indicator=True
    )

    missing_records = merged.loc[merged["_merge"] != "both", "student_id"].tolist()
    merged = merged.drop(columns="_merge")

    print("\n--- TASK 2: MERGE ---")
    print("Missing attendance records after merge:", missing_records)
    print("Merged dataset:")
    print(merged.to_string(index=False))

    if merged["attendance"].isna().any():
        raise ValueError("Some students have no attendance record.")

    return merged


def numpy_analysis(df):
    """Calculate required statistics using NumPy."""
    marks = df["marks"].to_numpy(dtype=float)
    attendance = df["attendance"].to_numpy(dtype=float)

    stats = {
        "mean_marks": np.mean(marks),
        "median_marks": np.median(marks),
        "std_marks": np.std(marks),
        "max_marks": np.max(marks),
        "min_marks": np.min(marks),
        "mean_attendance": np.mean(attendance),
    }

    print("\n--- TASK 3: NUMPY ANALYSIS ---")
    for key, value in stats.items():
        print(f"{key}: {value:.2f}")

    return stats


def scholarship_rule_map(scholarships):
    """Convert scholarship rules to a department-keyed mapping."""
    return {rule["department"]: rule for rule in scholarships}


def apply_scholarships(df, scholarships):
    """Apply department-specific scholarship conditions and bonus marks."""
    rules = scholarship_rule_map(scholarships)

    def evaluate_student(row):
        rule = rules.get(row["department"])
        if rule is None:
            return pd.Series({"scholarship_status": "Not Eligible",
                              "final_marks": row["marks"]})

        eligible = (
            row["marks"] >= rule["minimum_marks"]
            and row["attendance"] >= rule["minimum_attendance"]
        )

        return pd.Series({
            "scholarship_status": "Eligible" if eligible else "Not Eligible",
            "final_marks": row["marks"] + rule["bonus_marks"] if eligible else row["marks"]
        })

    # Meaningful lambda usage: classify each student's scholarship row.
    scholarship_rows = df.apply(lambda row: evaluate_student(row), axis=1)
    result = pd.concat([df, scholarship_rows], axis=1)

    print("\n--- TASK 4: SCHOLARSHIP ELIGIBILITY ---")
    print(
        result[
            ["student_id", "name", "department", "marks",
             "attendance", "scholarship_status", "final_marks"]
        ].to_string(index=False)
    )

    return result


def add_performance_category(df):
    """Classify students according to final marks."""
    def classify(marks):
        if marks >= 90:
            return "Outstanding"
        if marks >= 80:
            return "Excellent"
        if marks >= 70:
            return "Good"
        if marks >= 60:
            return "Average"
        return "Needs Improvement"

    df["performance"] = df["final_marks"].apply(classify)

    print("\n--- TASK 5: PERFORMANCE CATEGORY ---")
    print(df[["student_id", "name", "final_marks", "performance"]].to_string(index=False))

    return df


def pandas_analytics(df):
    """Perform required Pandas analytics, including meaningful map/filter usage."""
    top_5 = df.nlargest(5, "final_marks")[
        ["student_id", "name", "department", "final_marks"]
    ]

    department_average = (
        df.groupby("department", as_index=False)["final_marks"]
        .mean()
        .rename(columns={"final_marks": "average_final_marks"})
    )

    city_average = (
        df.groupby("city", as_index=False)["final_marks"]
        .mean()
        .rename(columns={"final_marks": "average_final_marks"})
    )

    best_department = department_average.loc[
        department_average["average_final_marks"].idxmax(), "department"
    ]

    highest_attendance_row = df.loc[df["attendance"].idxmax()]
    scholarship_count = int((df["scholarship_status"] == "Eligible").sum())
    performance_counts = df["performance"].value_counts()

    # Meaningful map(): convert department averages into rounded display values.
    department_average["average_final_marks"] = department_average[
        "average_final_marks"
    ].map(lambda value: round(value, 2))

    # Meaningful filter(): select students whose final marks are above 85.
    high_performers = list(
        filter(lambda row: row["final_marks"] > 85, df.to_dict("records"))
    )

    print("\n--- TASK 6: PANDAS ANALYTICS ---")
    print("\nTop 5 students:")
    print(top_5.to_string(index=False))

    print("\nDepartment-wise average final marks:")
    print(department_average.to_string(index=False))

    print("\nCity-wise average final marks:")
    print(city_average.to_string(index=False))

    print("\nDepartment with highest average final marks:", best_department)
    print(
        "Student with highest attendance:",
        highest_attendance_row["name"],
        f"({highest_attendance_row['attendance']})"
    )
    print("Number of scholarship-eligible students:", scholarship_count)

    print("\nStudents in each performance category:")
    print(performance_counts.to_string())

    print("\nStudents with final marks > 85 (filter()):", len(high_performers))

    return {
        "top_5": top_5,
        "department_average": department_average,
        "city_average": city_average,
        "best_department": best_department,
        "highest_attendance_row": highest_attendance_row,
        "scholarship_count": scholarship_count,
        "performance_counts": performance_counts,
    }


def create_database(df):
    """Create SQLite database and store the final processed dataset."""
    print("\n--- TASK 7: SQLITE DATABASE ---")

    columns = [
        "student_id", "name", "department", "city", "marks",
        "attendance", "scholarship_status", "final_marks", "performance"
    ]

    with sqlite3.connect(DATABASE_FILE) as connection:
        df[columns].to_sql(
            "student_performance",
            connection,
            if_exists="replace",
            index=False
        )

        eligible = pd.read_sql_query(
            """
            SELECT student_id, name, department, final_marks, scholarship_status
            FROM student_performance
            WHERE scholarship_status = 'Eligible'
            """,
            connection
        )

        marks_above_85 = pd.read_sql_query(
            """
            SELECT student_id, name, department, final_marks
            FROM student_performance
            WHERE final_marks > 85
            ORDER BY final_marks DESC
            """,
            connection
        )

        department_sql = pd.read_sql_query(
            """
            SELECT department, ROUND(AVG(final_marks), 2) AS average_final_marks
            FROM student_performance
            GROUP BY department
            ORDER BY average_final_marks DESC
            """,
            connection
        )

    print("\nQuery 1 - Scholarship-eligible students:")
    print(eligible.to_string(index=False))

    print("\nQuery 2 - Final marks > 85:")
    print(marks_above_85.to_string(index=False))

    print("\nQuery 3 - Department-wise average final marks:")
    print(department_sql.to_string(index=False))


def create_visualizations(df, analytics):
    """Generate and save the required Matplotlib charts."""
    print("\n--- TASK 8: VISUALIZATION ---")

    department_average = analytics["department_average"]

    plt.figure(figsize=(8, 5))
    plt.bar(
        department_average["department"],
        department_average["average_final_marks"]
    )
    plt.title("Department vs Average Final Marks")
    plt.xlabel("Department")
    plt.ylabel("Average Final Marks")
    plt.ylim(0, 100)
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(DEPARTMENT_CHART, dpi=150)
    plt.close()

    performance_order = [
        "Outstanding",
        "Excellent",
        "Good",
        "Average",
        "Needs Improvement"
    ]
    performance_counts = (
        df["performance"]
        .value_counts()
        .reindex(performance_order, fill_value=0)
    )

    plt.figure(figsize=(7, 7))
    plt.pie(
        performance_counts.values,
        labels=performance_counts.index,
        autopct="%1.1f%%",
        startangle=90
    )
    plt.title("Performance Category Distribution")
    plt.tight_layout()
    plt.savefig(PERFORMANCE_CHART, dpi=150)
    plt.close()

    print("Saved:", DEPARTMENT_CHART.name)
    print("Saved:", PERFORMANCE_CHART.name)


def generate_report(df, stats, analytics):
    """Generate a dynamic management report as JSON."""
    top_student_row = df.loc[df["final_marks"].idxmax()]
    highest_attendance_row = analytics["highest_attendance_row"]

    report = {
        "total_students": int(len(df)),
        "average_marks": round(float(stats["mean_marks"]), 2),
        "average_attendance": round(float(stats["mean_attendance"]), 2),
        "scholarship_students": int(analytics["scholarship_count"]),
        "top_student": str(top_student_row["name"]),
        "best_department": str(analytics["best_department"]),
        "highest_attendance_student": str(highest_attendance_row["name"]),
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\n--- TASK 9: MANAGEMENT REPORT ---")
    print(json.dumps(report, indent=4))
    print("Saved:", REPORT_FILE.name)


def main():
    students, attendance, scholarships = load_data()
    validate_data(students, attendance, scholarships)

    inspect_data(students, scholarships)

    merged = merge_student_data(students, attendance)
    stats = numpy_analysis(merged)

    processed = apply_scholarships(merged, scholarships)
    processed = add_performance_category(processed)

    analytics = pandas_analytics(processed)
    create_database(processed)
    create_visualizations(processed, analytics)
    generate_report(processed, stats, analytics)

    print("\nPipeline completed successfully.")
    print("Generated files:")
    for path in [
        DATABASE_FILE,
        REPORT_FILE,
        DEPARTMENT_CHART,
        PERFORMANCE_CHART,
    ]:
        print(" -", path.name)


if __name__ == "__main__":
    main()
