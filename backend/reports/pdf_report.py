from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet


# -----------------------
# Single Resume PDF
# -----------------------
def create_pdf(
    score,
    matched,
    missing,
    suggestions,
    experience_level,
    filename="report.pdf"
):

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            f"ATS Score: {score}%",
            styles["Title"]
        )
    )

    content.append(
        Spacer(1, 12)
    )

    content.append(
        Paragraph(
            f"Experience Level: {experience_level}",
            styles["Heading2"]
        )
    )

    content.append(
        Spacer(1, 12)
    )

    # Matched Skills
    content.append(
        Paragraph(
            "Matched Skills:",
            styles["Heading2"]
        )
    )

    for skill in matched:

        content.append(
            Paragraph(
                skill,
                styles["Normal"]
            )
        )

    content.append(
        Spacer(1, 12)
    )

    # Missing Skills
    content.append(
        Paragraph(
            "Missing Skills:",
            styles["Heading2"]
        )
    )

    for skill in missing:

        content.append(
            Paragraph(
                skill,
                styles["Normal"]
            )
        )

    content.append(
        Spacer(1, 12)
    )

    # Suggestions
    content.append(
        Paragraph(
            "Suggestions:",
            styles["Heading2"]
        )
    )

    for suggestion in suggestions:

        content.append(
            Paragraph(
                suggestion,
                styles["Normal"]
            )
        )

    doc.build(content)

    return filename


# -----------------------
# Comparison PDF
# -----------------------
def create_comparison_pdf(
    results,
    filename="comparison_report.pdf"
):

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    content = []

    for result in results:

        content.append(
            Paragraph(
                f"Resume: {result['filename']}",
                styles["Heading2"]
            )
        )

        content.append(
            Paragraph(
                f"ATS Score: {result['score']}%",
                styles["Normal"]
            )
        )

        content.append(
            Paragraph(
                f"Experience Level: {result['experience_level']}",
                styles["Normal"]
            )
        )

        # Matched Skills
        content.append(
            Paragraph(
                "Matched Skills:",
                styles["Heading3"]
            )
        )

        for skill in result['matched_skills']:

            content.append(
                Paragraph(
                    skill,
                    styles["Normal"]
                )
            )

        # Missing Skills
        content.append(
            Paragraph(
                "Missing Skills:",
                styles["Heading3"]
            )
        )

        for skill in result['missing_skills']:

            content.append(
                Paragraph(
                    skill,
                    styles["Normal"]
                )
            )

        # Suggestions
        content.append(
            Paragraph(
                "Suggestions:",
                styles["Heading3"]
            )
        )

        for suggestion in result['suggestions']:

            content.append(
                Paragraph(
                    suggestion,
                    styles["Normal"]
                )
            )

        content.append(
            Spacer(1, 20)
        )

    doc.build(content)

    return filename