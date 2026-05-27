from flask import Blueprint, request, send_file

from reports.pdf_report import (
    create_pdf,
    create_comparison_pdf
)

download_bp = Blueprint(
    "download",
    __name__
)


# -----------------------
# Download Single Report
# -----------------------
@download_bp.route(
    '/download',
    methods=['POST']
)
def download():

    data = request.json

    file_path = create_pdf(

        data['score'],

        data['matched_skills'],

        data['missing_skills'],

        data['suggestions'],

        data.get(
            'experience_level',
            'N/A'
        )
    )

    return send_file(
        file_path,
        as_attachment=True
    )


# -----------------------
# Download Comparison Report
# -----------------------
@download_bp.route(
    '/download_comparison',
    methods=['POST']
)
def download_comparison():

    data = request.json

    file_path = create_comparison_pdf(
        data['comparison']
    )

    return send_file(
        file_path,
        as_attachment=True
    )