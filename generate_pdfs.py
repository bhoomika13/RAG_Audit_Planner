"""
Generates 9 separate PDF documents from the CFO Policy Framework content
(POL-ORD-001/002/003 v1.0 & v2.0, and WP-ORD-001/002/003 prior audit work papers).

Output naming convention:
  Policies    : POL-ORD-<id>_v<version>_<Name>.pdf
  Work papers : WP-ORD-<MonYYYY>.pdf
"""

import os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable,
    ListItem, PageBreak
)
from reportlab.lib.enums import TA_LEFT

OUT_DIR = os.path.join(os.path.dirname(__file__), "output_pdfs")
os.makedirs(OUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="DocTitle", fontSize=20, leading=24, spaceAfter=4,
                           textColor=colors.HexColor("#1a2b47"), fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="Kicker", fontSize=10, textColor=colors.HexColor("#5a6b85"),
                           spaceAfter=10, fontName="Helvetica"))
styles.add(ParagraphStyle(name="SubTitle", fontSize=12, textColor=colors.HexColor("#5a6b85"),
                           spaceAfter=14, fontName="Helvetica-Oblique"))
styles.add(ParagraphStyle(name="H1", fontSize=15, leading=18, spaceBefore=14, spaceAfter=8,
                           textColor=colors.HexColor("#1a2b47"), fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="H2", fontSize=12, leading=15, spaceBefore=10, spaceAfter=6,
                           textColor=colors.HexColor("#2a6f97"), fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="Body", fontSize=9.5, leading=13.5, spaceAfter=6,
                           alignment=TA_LEFT, fontName="Helvetica"))
styles.add(ParagraphStyle(name="BulletItem", fontSize=9.5, leading=13, fontName="Helvetica"))
styles.add(ParagraphStyle(name="Footer", fontSize=8, textColor=colors.HexColor("#888888")))
styles.add(ParagraphStyle(name="CalloutTitle", fontSize=9, fontName="Helvetica-Bold", spaceAfter=2))
styles.add(ParagraphStyle(name="CalloutBody", fontSize=9, leading=12))

STATUS_COLORS = {
    "SUPERSEDED": (colors.HexColor("#fdeaea"), colors.HexColor("#8a2b2b")),
    "ACTIVE": (colors.HexColor("#e7f5ea"), colors.HexColor("#215732")),
}


def callout(title, body, kind="neutral"):
    bg = colors.HexColor("#eef2f7")
    if kind == "danger":
        bg = colors.HexColor("#fdeaea")
    elif kind == "success":
        bg = colors.HexColor("#e7f5ea")
    elif kind == "warning":
        bg = colors.HexColor("#fdf3d9")
    t = Table(
        [[Paragraph(f"<b>{title}</b>", styles["CalloutTitle"])],
         [Paragraph(body, styles["CalloutBody"])]],
        colWidths=[6.6 * inch],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9c9c9")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def info_table(rows):
    t = Table(rows, colWidths=[1.3 * inch, 2.1 * inch, 1.3 * inch, 2.1 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f2f2")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f2f2f2")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def data_table(header, rows, col_widths=None):
    data = [header] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2b47")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9c9c9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
    ]
    t.setStyle(TableStyle(style))
    return t


def bullets(items):
    # Plain ASCII "-" marker (not "*", not ListFlowable auto-bullets): the U+2022
    # bullet glyph has a broken ToUnicode mapping in ReportLab's base-14 fonts and
    # extracts as an unmapped "(cid:127)" artifact in pdfplumber/most PDF text tools.
    rows = [[Paragraph("-", styles["BulletItem"]), Paragraph(i, styles["BulletItem"])] for i in items]
    t = Table(rows, colWidths=[0.18 * inch, 6.4 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def build_doc(filename, footer_text, story):
    path = os.path.join(OUT_DIR, filename)

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(0.75 * inch, 0.5 * inch, footer_text)
        canvas.drawRightString(LETTER[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        path, pagesize=LETTER,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"Created: {path}")


# ---------------------------------------------------------------------------
# 1. POL-ORD-001 v1.0
# ---------------------------------------------------------------------------
def doc_pol001_v1():
    story = [
        Paragraph("CFO POLICY FRAMEWORK", styles["Kicker"]),
        Paragraph("ORDER INTAKE<br/>RECOGNITION &amp; MEASUREMENT", styles["DocTitle"]),
        Paragraph("Policy &amp; Control Standard", styles["SubTitle"]),
        info_table([
            ["POLICY ID", "POL-ORD-001", "VERSION", "1.0"],
            ["STATUS", "SUPERSEDED", "EFFECTIVE", "January 2023"],
            ["SUPERSEDED", "January 2025", "CONTROL ID", "CTRL-REV-014"],
            ["PROCESS AREA", "Order-to-Cash (O2C)", "OWNER", "Group Finance – Revenue Assurance"],
        ]),
        Spacer(1, 10),
        callout("DOCUMENT STATUS",
                "This policy is superseded effective January 2025. It is retained for historical "
                "reference and control traceability.", "danger"),
        Spacer(1, 14),
        Paragraph("<i>Controlled Document</i><br/>For internal finance, revenue assurance, audit and "
                  "control-reference purposes.", styles["Body"]),
        PageBreak(),

        Paragraph("1. Purpose", styles["H1"]),
        Paragraph("This policy establishes the principles, criteria, and controls governing the "
                  "recognition and measurement of Order Intake across the Company.", styles["Body"]),

        Paragraph("2. Scope", styles["H1"]),
        Paragraph("This policy applies to all business units, regions, and legal entities that generate, "
                  "process, or record customer orders under the Order-to-Cash (O2C) cycle, including:",
                  styles["Body"]),
        bullets(["Hardware and Software arrangements", "Standalone Services arrangements",
                 "Bundled multi-element arrangements"]),

        Paragraph("3. Definitions", styles["H1"]),
        Paragraph("3.1 Order", styles["H2"]),
        Paragraph("A binding agreement between the Company and a customer under which the Company "
                  "commits to deliver goods and/or services in exchange for consideration.", styles["Body"]),
        Paragraph("3.2 Order Backlog", styles["H2"]),
        Paragraph("The cumulative value of Orders recognized as Order Intake but not yet delivered, "
                  "fulfilled, or recognized as revenue.", styles["Body"]),

        Paragraph("4. Roles and Responsibilities", styles["H1"]),
        data_table(["Role", "Responsibility"], [
            ["Sales Operations", "Order capture and documentation collection"],
            ["Finance Business Partners", "Recognition criteria review"],
            ["Finance Manager", "Credit risk sign-off (see 5.3)"],
            ["Group Finance (Revenue Assurance)", "Policy ownership and testing"],
        ], col_widths=[2.6 * inch, 4.0 * inch]),

        Paragraph("5. Order Intake Recognition and Measurement", styles["H1"]),
        Paragraph("5.1 Recognition Criteria for Order Intake", styles["H2"]),
        Paragraph("An order shall be recognized as Order Intake when:", styles["Body"]),
        bullets(["a) A legally binding contract or Purchase Order (PO) exists, AND",
                 "b) The order value can be reliably measured."]),
        Paragraph("Orders not meeting both (a) and (b) shall remain in the sales pipeline and shall not "
                  "be recorded as Order Intake.", styles["Body"]),

        Paragraph("5.2 Customer Commitment", styles["H2"]),
        Paragraph("Customer commitment is evidenced by receipt of a signed Purchase Order alone. A "
                  "countersigned contract is preferred but not mandatory, provided the PO specifies:",
                  styles["Body"]),
        bullets(["Price", "Quantity", "Delivery terms"]),

        Paragraph("5.3 Collectability Assessment", styles["H2"]),
        Paragraph("5.3.1 Assessment Basis", styles["H2"]),
        Paragraph("Collectability is assessed based solely on the customer's credit rating at time of "
                  "order receipt, as classified below:", styles["Body"]),
        data_table(["Credit Rating", "Risk Classification", "Action Required"], [
            ["A", "Low Risk", "None"],
            ["B", "Medium Risk", "Standard booking"],
            ["Below B", "High Risk", "Finance Manager review"],
        ], col_widths=[1.7 * inch, 2.3 * inch, 2.6 * inch]),

        Paragraph("5.3.2 Escalation Requirements", styles["H2"]),
        Paragraph("Orders from customers rated below \"B\" require Finance Manager sign-off prior to "
                  "booking. No additional escalation is required regardless of order value.", styles["Body"]),

        Paragraph("5.4 Timing for Booking of Order Intake", styles["H2"]),
        Paragraph("Order Intake shall be booked immediately upon receipt of a valid Purchase Order, "
                  "regardless of contract signature status. This approach prioritizes:", styles["Body"]),
        bullets(["Timeliness of reporting, over", "Administrative completeness of documentation"]),
        Spacer(1, 6),
        callout("CONTROL PRINCIPLE",
                "A valid Purchase Order is the primary trigger for Order Intake booking, subject to the "
                "recognition criteria and collectability requirements defined above."),

        Paragraph("6. Order Intake Approvals", styles["H1"]),
        Paragraph("Refer to POL-ORD-003 (Order Intake Approval &amp; Backlog Management Policy) for the "
                  "applicable delegation of authority matrix.", styles["Body"]),

        Paragraph("7. Exceptions and Escalation", styles["H1"]),
        Paragraph("Deviations from this policy require Finance Manager approval, with escalation to "
                  "Group Finance for exceptions exceeding $100,000 in order value.", styles["Body"]),

        Paragraph("8. Related Policies", styles["H1"]),
        bullets(["POL-ORD-002: Order Intake Value &amp; SSP Allocation Policy",
                 "POL-ORD-003: Order Intake Approval &amp; Backlog Management Policy"]),

        Paragraph("9. Revision History", styles["H1"]),
        data_table(["Version", "Date", "Summary of Change"], [
            ["1.0", "Jan 2023", "Initial policy issuance"],
        ], col_widths=[0.9 * inch, 1.1 * inch, 4.6 * inch]),
        Spacer(1, 10),
        callout("END OF CONTROLLED DOCUMENT", "Policy ID: POL-ORD-001 | Version: 1.0 | Status: Superseded"),
    ]
    build_doc("POL-ORD-001_v1.0_Order-Intake-Recognition-Measurement.pdf",
              "CFO POLICY FRAMEWORK | POL-ORD-001", story)


# ---------------------------------------------------------------------------
# 2. POL-ORD-001 v2.0
# ---------------------------------------------------------------------------
def doc_pol001_v2():
    story = [
        Paragraph("CFO POLICY FRAMEWORK", styles["Kicker"]),
        Paragraph("ORDER INTAKE<br/>RECOGNITION &amp; MEASUREMENT", styles["DocTitle"]),
        Paragraph("Policy &amp; Control Standard", styles["SubTitle"]),
        info_table([
            ["POLICY ID", "POL-ORD-001", "VERSION", "2.0"],
            ["STATUS", "ACTIVE / IN FORCE", "EFFECTIVE", "January 2025"],
            ["CONTROL ID", "CTRL-REV-014", "PROCESS AREA", "Order-to-Cash (O2C)"],
            ["OWNER", "Group Finance – Revenue Assurance", "CHANGE BASIS", "2024 internal audit cycle"],
        ]),
        Spacer(1, 10),
        callout("ACTIVE / IN FORCE",
                "Current controlled version. Use this version for current audit planning and control testing.",
                "success"),
        PageBreak(),

        Paragraph("1. Purpose", styles["H1"]),
        Paragraph("This policy establishes the principles, criteria, and controls governing the "
                  "recognition and measurement of Order Intake across the Company. This version "
                  "supersedes v1.0 and introduces enhanced controls following the 2024 internal audit "
                  "cycle.", styles["Body"]),

        Paragraph("2. Scope", styles["H1"]),
        Paragraph("This policy applies to all business units, regions, and legal entities that generate, "
                  "process, or record customer orders under the Order-to-Cash (O2C) cycle, including:",
                  styles["Body"]),
        bullets(["Hardware and Software arrangements", "Standalone Services arrangements",
                 "Bundled multi-element arrangements"]),

        Paragraph("3. Definitions", styles["H1"]),
        Paragraph("3.1 Order", styles["H2"]),
        Paragraph("A binding agreement between the Company and a customer, evidenced by BOTH a Purchase "
                  "Order AND a countersigned contract (see 5.2).", styles["Body"]),
        Paragraph("3.2 Order Backlog", styles["H2"]),
        Paragraph("The cumulative value of Orders recognized as Order Intake but not yet delivered, "
                  "fulfilled, or recognized as revenue.", styles["Body"]),

        Paragraph("4. Roles and Responsibilities", styles["H1"]),
        data_table(["Role", "Responsibility"], [
            ["Sales Operations", "Order capture; ensures PO + contract obtained"],
            ["Finance Business Partners", "Recognition criteria review"],
            ["Regional Finance Head", "Risk sign-off (elevated from v1.0)"],
            ["Group Treasury", "Publishes month-end FX spot rates"],
            ["Group Finance (Revenue Assurance)", "Policy ownership and testing"],
        ], col_widths=[2.6 * inch, 4.0 * inch]),

        Paragraph("5. Order Intake Recognition and Measurement", styles["H1"]),
        Paragraph("5.1 Recognition Criteria for Order Intake", styles["H2"]),
        Paragraph("An order shall be recognized as Order Intake when ALL of the following conditions "
                  "are met:", styles["Body"]),
        bullets(["A legally binding contract or Purchase Order (PO) exists, AND",
                 "The order value can be reliably measured, AND",
                 "Collectability is reasonably assured (see 5.3)."]),
        callout("KEY CHANGE FROM v1.0",
                "Collectability is now a recognition precondition, not merely a downstream approval "
                "trigger.", "warning"),

        Paragraph("5.2 Customer Commitment", styles["H2"]),
        Paragraph("Customer commitment must be evidenced by BOTH:", styles["Body"]),
        bullets(["A signed Purchase Order", "A countersigned contract"]),
        Paragraph("Orders supported by a PO alone do NOT qualify for recognition.", styles["Body"]),

        Paragraph("5.3 Collectability Assessment", styles["H2"]),
        Paragraph("5.3.1 Risk Scoring Model", styles["H2"]),
        Paragraph("Collectability is assessed using a combined weighted risk score:", styles["Body"]),
        Paragraph("Risk Score = (0.40 × Credit Rating Score) + (0.35 × Payment History Score) + "
                  "(0.25 × Country Risk Score)", styles["Body"]),
        Paragraph("Each component is scored on a 0–100 scale. Credit Rating Score is derived from Group "
                  "Credit Risk classification; Payment History Score is based on trailing 12-month "
                  "payment behavior; Country Risk Score is published quarterly by Group Treasury.",
                  styles["Body"]),
        data_table(["Risk Score Range", "Classification", "Action Required"], [
            ["80–100", "Low Risk", "None"],
            ["50–79", "Medium Risk", "Standard booking"],
            ["Below 50", "High Risk", "Regional Finance Head review"],
        ], col_widths=[1.9 * inch, 2.1 * inch, 2.6 * inch]),

        Paragraph("5.3.2 Escalation Requirements", styles["H2"]),
        Paragraph("Orders scoring below 50 require MANDATORY Regional Finance Head sign-off prior to "
                  "booking.", styles["Body"]),

        Paragraph("5.4 Timing for Booking of Order Intake", styles["H2"]),
        Paragraph("Order Intake shall be booked ONLY once BOTH of the following are received and "
                  "verified by Finance:", styles["Body"]),
        bullets(["Signed Purchase Order", "Countersigned contract"]),

        Paragraph("5.5 Orders in Non-Euro Currencies", styles["H2"]),
        Paragraph("5.5.1 Conversion Methodology", styles["H2"]),
        Paragraph("Converted Order Value (EUR) = Order Value (Local Currency) ÷ Month-End Spot Rate",
                  styles["Body"]),
        Paragraph("The Month-End Spot Rate is published by Group Treasury as of the booking date.",
                  styles["Body"]),

        Paragraph("5.5.2 FX Variance Control", styles["H2"]),
        Paragraph("FX Variance (%) = |Booking Rate − Order Date Rate| ÷ Order Date Rate × 100",
                  styles["Body"]),
        Paragraph("If FX Variance (%) &gt; 5%, the order must be:", styles["Body"]),
        bullets(["Flagged in the system", "Routed to the Controller for review prior to final booking"]),

        Paragraph("6. Order Intake Approvals", styles["H1"]),
        Paragraph("Refer to POL-ORD-003 v2.0 for the revised delegation of authority matrix and "
                  "thresholds.", styles["Body"]),

        Paragraph("7. Exceptions and Escalation", styles["H1"]),
        Paragraph("Deviations require Regional Finance Head approval, with escalation to Group Finance "
                  "for exceptions exceeding $100,000 in order value.", styles["Body"]),

        Paragraph("8. Related Policies", styles["H1"]),
        bullets(["POL-ORD-002: Order Intake Value &amp; SSP Allocation Policy",
                 "POL-ORD-003: Order Intake Approval &amp; Backlog Management Policy"]),

        Paragraph("9. Revision History", styles["H1"]),
        data_table(["Version", "Date", "Summary of Change"], [
            ["1.0", "Jan 2023", "Initial policy issuance"],
            ["2.0", "Jan 2025", "Dual-document commitment; weighted risk scoring; new FX conversion "
                                "section; elevated approval authority"],
        ], col_widths=[0.9 * inch, 1.1 * inch, 4.6 * inch]),
        Spacer(1, 10),
        callout("CONTROLLED DOCUMENT", "POL-ORD-001 | VERSION 2.0 | ACTIVE / IN FORCE", "success"),
    ]
    build_doc("POL-ORD-001_v2.0_Order-Intake-Recognition-Measurement.pdf",
              "CFO POLICY FRAMEWORK | CONTROLLED DOCUMENT", story)


# ---------------------------------------------------------------------------
# 3. POL-ORD-002 v1.0
# ---------------------------------------------------------------------------
def doc_pol002_v1():
    story = [
        Paragraph("CFO POLICY FRAMEWORK", styles["Kicker"]),
        Paragraph("ORDER INTAKE VALUE &amp; SSP<br/>ALLOCATION", styles["DocTitle"]),
        Paragraph("Policy &amp; Control Standard", styles["SubTitle"]),
        info_table([
            ["POLICY ID", "POL-ORD-002", "VERSION", "1.0"],
            ["STATUS", "SUPERSEDED", "EFFECTIVE", "March 2023"],
            ["SUPERSEDED", "June 2025", "CONTROL ID", "CTRL-REV-015"],
            ["PROCESS AREA", "Order-to-Cash (O2C)", "OWNER", "Group Finance – Revenue Assurance"],
        ]),
        Spacer(1, 10),
        callout("SUPERSEDED", "Historical version retained for audit trail, prior-period testing and "
                              "control traceability.", "danger"),
        PageBreak(),

        Paragraph("1. Purpose", styles["H1"]),
        Paragraph("This policy defines the methodology used to measure the value of Order Intake for "
                  "multi-element arrangements, including allocation of contract value across "
                  "deliverables using Standalone Selling Price (SSP).", styles["Body"]),

        Paragraph("2. Scope", styles["H1"]),
        Paragraph("Applies to all multi-element customer arrangements combining:", styles["Body"]),
        bullets(["Hardware/Software (HW/SW) deliverables, AND", "Services deliverables"]),

        Paragraph("3. Definitions", styles["H1"]),
        Paragraph("Standalone Selling Price (SSP): The price at which the Company would sell a "
                  "deliverable separately under similar circumstances.", styles["Body"]),

        Paragraph("4. Roles and Responsibilities", styles["H1"]),
        data_table(["Role", "Responsibility"], [
            ["Deal Desk", "Prepares SSP allocation calculations"],
            ["Finance Manager", "Reviews allocations exceeding variance threshold"],
            ["Pricing Team", "Maintains standard list price catalogue"],
        ], col_widths=[2.2 * inch, 4.4 * inch]),

        Paragraph("5. SSP Allocation Methodology", styles["H1"]),
        Paragraph("5.1 Calculation Basis", styles["H2"]),
        Paragraph("Allocation is performed using the Standalone List Price method. Each deliverable is "
                  "allocated a share of total contract value based on its list price relative to total "
                  "list price of all deliverables. No weighting adjustment is applied.", styles["Body"]),

        Paragraph("5.2 Allocation Formula", styles["H2"]),
        Paragraph("SSP Allocation (Deliverable) = (List Price of Deliverable ÷ Total List Price of All "
                  "Deliverables) × Total Contract Value", styles["Body"]),

        Paragraph("6. Sample Allocation Illustration", styles["H1"]),
        data_table(["Deliverable", "Contract Value", "SSP", "SSP Allocation"], [
            ["HW/SW", "30", "30", "27.90"],
            ["Services", "1", "10", "3.10"],
            ["Total", "31", "40", "31.00"],
        ], col_widths=[2.0 * inch, 1.6 * inch, 1.4 * inch, 1.6 * inch]),
        Paragraph("The allocation reflects a proportional split based on the list price ratio of 30:10, "
                  "applied against total contract value of 31.", styles["Body"]),

        Paragraph("7. Approval Requirements", styles["H1"]),
        Paragraph("Allocations resulting in variance greater than 20% from standard list price ratios "
                  "require Finance Manager sign-off prior to booking.", styles["Body"]),

        Paragraph("8. Related Policies", styles["H1"]),
        bullets(["POL-ORD-001: Order Intake Recognition &amp; Measurement Policy",
                 "POL-ORD-003: Order Intake Approval &amp; Backlog Management Policy"]),

        Paragraph("9. Revision History", styles["H1"]),
        data_table(["Version", "Date", "Summary of Change"], [
            ["1.0", "Mar 2023", "Initial policy issuance"],
        ], col_widths=[0.9 * inch, 1.1 * inch, 4.6 * inch]),
        Spacer(1, 10),
        callout("CONTROLLED DOCUMENT", "POL-ORD-002 | VERSION 1.0 | SUPERSEDED", "danger"),
    ]
    build_doc("POL-ORD-002_v1.0_Order-Intake-Value-SSP-Allocation.pdf",
              "CFO POLICY FRAMEWORK | CONTROLLED DOCUMENT", story)


# ---------------------------------------------------------------------------
# 4. POL-ORD-002 v2.0
# ---------------------------------------------------------------------------
def doc_pol002_v2():
    story = [
        Paragraph("CFO POLICY FRAMEWORK", styles["Kicker"]),
        Paragraph("ORDER INTAKE VALUE &amp; SSP<br/>ALLOCATION", styles["DocTitle"]),
        Paragraph("Policy &amp; Control Standard", styles["SubTitle"]),
        info_table([
            ["POLICY ID", "POL-ORD-002", "VERSION", "2.0"],
            ["STATUS", "ACTIVE / IN FORCE", "EFFECTIVE", "June 2025"],
            ["CONTROL ID", "CTRL-REV-015", "PROCESS AREA", "Order-to-Cash (O2C)"],
            ["OWNER", "Group Finance – Revenue Assurance", "CHANGE BASIS",
             "Q1 2025 internal audit recommendations"],
        ]),
        Spacer(1, 10),
        callout("ACTIVE / IN FORCE",
                "Current controlled version. Use this version for current audit planning and control "
                "testing.", "success"),
        PageBreak(),

        Paragraph("1. Purpose", styles["H1"]),
        Paragraph("This policy defines the methodology used to measure the value of Order Intake for "
                  "multi-element arrangements. This version supersedes v1.0 and introduces a weighted "
                  "allocation methodology following Q1 2025 internal audit recommendations.", styles["Body"]),

        Paragraph("2. Scope", styles["H1"]),
        Paragraph("Applies to all multi-element customer arrangements combining:", styles["Body"]),
        bullets(["Hardware/Software (HW/SW) deliverables, AND", "Services deliverables"]),

        Paragraph("3. Definitions", styles["H1"]),
        Paragraph("Standalone Selling Price (SSP): The price at which the Company would sell a "
                  "deliverable separately under similar circumstances.", styles["Body"]),
        Paragraph("Weighted Factor: An adjustment factor applied per deliverable category to reflect "
                  "margin and risk differences, determined annually by the Pricing Committee.", styles["Body"]),

        Paragraph("4. Roles and Responsibilities", styles["H1"]),
        data_table(["Role", "Responsibility"], [
            ["Deal Desk", "Prepares Relative SSP allocation calculations"],
            ["Regional Finance Head", "Reviews allocations exceeding threshold (elevated from Finance Manager)"],
            ["Pricing Committee", "Determines annual Weighted Factors"],
        ], col_widths=[2.2 * inch, 4.4 * inch]),

        Paragraph("5. SSP Allocation Methodology", styles["H1"]),
        Paragraph("5.1 Calculation Basis", styles["H2"]),
        Paragraph("Allocation is performed using the Relative SSP method, under which a Weighted Factor "
                  "is applied per deliverable category. This replaces the unweighted Standalone List "
                  "Price method used in v1.0.", styles["Body"]),

        Paragraph("5.2 Weighted Factor Determination", styles["H2"]),
        Paragraph("The Weighted Factor is determined annually by the Pricing Committee based on:",
                  styles["Body"]),
        bullets(["Historical margin performance by deliverable category", "Delivery risk profile",
                 "Market comparables"]),

        Paragraph("5.3 Allocation Formula", styles["H2"]),
        Paragraph("Step 1 — Relative SSP: Relative SSP = SSP × Weighted Factor", styles["Body"]),
        Paragraph("Step 2 — SSP Allocation: SSP Allocation = (Relative SSP ÷ Total Relative SSP) × Total "
                  "Contract Value", styles["Body"]),
        Paragraph("Step 3 — Variance Check: SSP % from Contract Value = (SSP Allocation − Proportional "
                  "Contract Value) ÷ Proportional Contract Value × 100", styles["Body"]),

        Paragraph("6. Sample Allocation Illustration", styles["H1"]),
        data_table(
            ["Deliverable", "Contract Value", "SSP", "Weighted Factor", "Relative SSP", "SSP Allocation",
             "SSP % from Contract Value"],
            [
                ["HW/SW", "30", "30", "75.0%", "23.25", "-6.75", "-22.5%"],
                ["Services", "1", "10", "25.0%", "7.75", "6.75", "675.0%"],
                ["Total", "31", "40", "100.0%", "31.00", "", ""],
            ],
            col_widths=[0.9 * inch, 0.85 * inch, 0.6 * inch, 1.0 * inch, 0.85 * inch, 0.9 * inch, 1.1 * inch],
        ),
        Paragraph("Note: Figures are illustrative and demonstrate the mechanics of Weighted Factor "
                  "application; actual Weighted Factors are published annually by the Pricing Committee.",
                  styles["Body"]),

        Paragraph("7. Approval Requirements", styles["H1"]),
        Paragraph("Allocations resulting in variance greater than 10% from Relative SSP require Regional "
                  "Finance Head sign-off prior to booking.", styles["Body"]),
        callout("CONTROL ENHANCEMENT",
                "Threshold reduced from 20% to 10%; approval authority elevated from Finance Manager to "
                "Regional Finance Head.", "warning"),

        Paragraph("8. Related Policies", styles["H1"]),
        bullets(["POL-ORD-001: Order Intake Recognition &amp; Measurement Policy",
                 "POL-ORD-003: Order Intake Approval &amp; Backlog Management Policy"]),

        Paragraph("9. Revision History", styles["H1"]),
        data_table(["Version", "Date", "Summary of Change"], [
            ["1.0", "Mar 2023", "Initial policy issuance"],
            ["2.0", "Jun 2025", "Relative SSP method with Weighted Factor; reduced approval variance "
                                "threshold to 10%"],
        ], col_widths=[0.9 * inch, 1.1 * inch, 4.6 * inch]),
        Spacer(1, 10),
        callout("CONTROLLED DOCUMENT", "POL-ORD-002 | VERSION 2.0 | ACTIVE / IN FORCE", "success"),
    ]
    build_doc("POL-ORD-002_v2.0_Order-Intake-Value-SSP-Allocation.pdf",
              "CFO POLICY FRAMEWORK | CONTROLLED DOCUMENT", story)


# ---------------------------------------------------------------------------
# 5. POL-ORD-003 v1.0
# ---------------------------------------------------------------------------
def doc_pol003_v1():
    story = [
        Paragraph("CFO POLICY FRAMEWORK", styles["Kicker"]),
        Paragraph("ORDER INTAKE APPROVAL &amp;<br/>BACKLOG MANAGEMENT", styles["DocTitle"]),
        Paragraph("Policy &amp; Control Standard", styles["SubTitle"]),
        info_table([
            ["POLICY ID", "POL-ORD-003", "VERSION", "1.0"],
            ["STATUS", "SUPERSEDED", "EFFECTIVE", "July 2023"],
            ["SUPERSEDED", "September 2025", "CONTROL ID", "CTRL-REV-016"],
            ["PROCESS AREA", "Order-to-Cash (O2C)", "OWNER", "Group Finance – Revenue Assurance"],
        ]),
        Spacer(1, 10),
        callout("SUPERSEDED", "Historical version retained for audit trail, prior-period testing and "
                              "control traceability.", "danger"),
        PageBreak(),

        Paragraph("1. Purpose", styles["H1"]),
        Paragraph("This policy defines approval authority levels for booking Order Intake and "
                  "establishes requirements for Order Backlog monitoring.", styles["Body"]),

        Paragraph("2. Scope", styles["H1"]),
        Paragraph("Applies to all Orders booked as Order Intake and to periodic review of Order Backlog "
                  "balances.", styles["Body"]),

        Paragraph("3. Approval Authority Matrix", styles["H1"]),
        data_table(["Order Value", "Approver"], [
            ["Up to $50,000", "Sales Manager"],
            ["$50,001 – $250,000", "Regional Finance Head"],
            ["Above $250,000", "CFO"],
        ], col_widths=[3.0 * inch, 3.6 * inch]),
        Paragraph("Approval must be documented and retained in the order file.", styles["Body"]),

        Paragraph("4. Order Backlog Management", styles["H1"]),
        Paragraph("4.1 Review Frequency", styles["H2"]),
        Paragraph("Order Backlog is reviewed on a quarterly basis by the Finance team.", styles["Body"]),
        Paragraph("4.2 Aging Calculation", styles["H2"]),
        Paragraph("Aging (Days) = Current Date − Original Order Booking Date", styles["Body"]),
        Paragraph("4.3 Flagging Criteria", styles["H2"]),
        Paragraph("Backlog items shall be flagged for review when:", styles["Body"]),
        bullets(["Aging (Days) &gt; 365 days (12 months), AND",
                 "No delivery milestone has been recorded in the system"]),
        Paragraph("Flagged items require Finance Manager review to determine whether continued "
                  "recognition remains appropriate.", styles["Body"]),

        Paragraph("5. Roles and Responsibilities", styles["H1"]),
        data_table(["Role", "Responsibility"], [
            ["Sales Manager", "Approves orders up to $50,000"],
            ["Regional Finance Head", "Approves orders $50,001–$250,000"],
            ["CFO", "Approves orders above $250,000"],
            ["Finance Team", "Performs quarterly Backlog review"],
        ], col_widths=[2.2 * inch, 4.4 * inch]),

        Paragraph("6. Related Policies", styles["H1"]),
        bullets(["POL-ORD-001: Order Intake Recognition &amp; Measurement Policy",
                 "POL-ORD-002: Order Intake Value &amp; SSP Allocation Policy"]),

        Paragraph("7. Revision History", styles["H1"]),
        data_table(["Version", "Date", "Summary of Change"], [
            ["1.0", "Jul 2023", "Initial policy issuance"],
        ], col_widths=[0.9 * inch, 1.1 * inch, 4.6 * inch]),
        Spacer(1, 10),
        callout("CONTROLLED DOCUMENT", "POL-ORD-003 | VERSION 1.0 | SUPERSEDED", "danger"),
    ]
    build_doc("POL-ORD-003_v1.0_Order-Intake-Approval-Backlog-Management.pdf",
              "CFO POLICY FRAMEWORK | CONTROLLED DOCUMENT", story)


# ---------------------------------------------------------------------------
# 6. POL-ORD-003 v2.0
# ---------------------------------------------------------------------------
def doc_pol003_v2():
    story = [
        Paragraph("CFO POLICY FRAMEWORK", styles["Kicker"]),
        Paragraph("ORDER INTAKE APPROVAL &amp;<br/>BACKLOG MANAGEMENT", styles["DocTitle"]),
        Paragraph("Policy &amp; Control Standard", styles["SubTitle"]),
        info_table([
            ["POLICY ID", "POL-ORD-003", "VERSION", "2.0"],
            ["STATUS", "ACTIVE / IN FORCE", "EFFECTIVE", "September 2025"],
            ["CONTROL ID", "CTRL-REV-016", "PROCESS AREA", "Order-to-Cash (O2C)"],
            ["OWNER", "Group Finance – Revenue Assurance", "PROGRAM", "FY2025 controls enhancement"],
        ]),
        Spacer(1, 10),
        callout("ACTIVE / IN FORCE",
                "Current controlled version. Use this version for current audit planning and control "
                "testing.", "success"),
        PageBreak(),

        Paragraph("1. Purpose", styles["H1"]),
        Paragraph("This policy defines approval authority levels for booking Order Intake and "
                  "establishes requirements for Order Backlog monitoring. This version supersedes v1.0 "
                  "as part of the FY2025 controls enhancement program.", styles["Body"]),

        Paragraph("2. Scope", styles["H1"]),
        Paragraph("Applies to all Orders booked as Order Intake and to periodic review of Order Backlog "
                  "balances.", styles["Body"]),

        Paragraph("3. Approval Authority Matrix", styles["H1"]),
        data_table(["Order Value", "Approver"], [
            ["Up to $100,000", "Sales Manager"],
            ["$100,001 – $500,000", "Regional Finance Head"],
            ["Above $500,000", "CFO"],
        ], col_widths=[3.0 * inch, 3.6 * inch]),
        callout("THRESHOLD UPDATE",
                "Approval thresholds increased from $50,000 / $250,000 to $100,000 / $500,000.", "warning"),
        Paragraph("Approval must be documented and retained in the order file.", styles["Body"]),

        Paragraph("4. Order Backlog Management", styles["H1"]),
        Paragraph("4.1 Review Frequency", styles["H2"]),
        Paragraph("Order Backlog is reviewed on a MONTHLY basis by the Finance team.", styles["Body"]),
        Paragraph("4.2 Aging Calculation", styles["H2"]),
        Paragraph("Aging (Days) = Current Date − Original Order Booking Date<br/>"
                  "Aging (Months) = Aging (Days) ÷ 30 (approximate)", styles["Body"]),
        Paragraph("4.3 Flagging Criteria", styles["H2"]),
        Paragraph("Backlog items shall be flagged for review when EITHER:", styles["Body"]),
        bullets(["Aging (Days) &gt; 180 days (6 months), OR",
                 "No delivery milestone has been recorded in the system for 2 consecutive monthly "
                 "review cycles"]),
        Paragraph("Flagged items require Finance Manager review to determine whether continued "
                  "recognition remains appropriate.", styles["Body"]),
        callout("CONTROL ENHANCEMENT",
                "Review frequency moved from quarterly to monthly; aging flag threshold reduced from "
                "365 days to 180 days.", "success"),

        Paragraph("5. Roles and Responsibilities", styles["H1"]),
        data_table(["Role", "Responsibility"], [
            ["Sales Manager", "Approves orders up to $100,000"],
            ["Regional Finance Head", "Approves orders $100,001–$500,000"],
            ["CFO", "Approves orders above $500,000"],
            ["Finance Team", "Performs MONTHLY Backlog review"],
        ], col_widths=[2.2 * inch, 4.4 * inch]),

        Paragraph("6. Related Policies", styles["H1"]),
        bullets(["POL-ORD-001: Order Intake Recognition &amp; Measurement Policy",
                 "POL-ORD-002: Order Intake Value &amp; SSP Allocation Policy"]),

        Paragraph("7. Revision History", styles["H1"]),
        data_table(["Version", "Date", "Summary of Change"], [
            ["1.0", "Jul 2023", "Initial policy issuance"],
            ["2.0", "Sep 2025", "Increased approval thresholds; monthly Backlog review; reduced aging "
                                "flag threshold to 6 months"],
        ], col_widths=[0.9 * inch, 1.1 * inch, 4.6 * inch]),
        Spacer(1, 10),
        callout("CONTROLLED DOCUMENT", "POL-ORD-003 | VERSION 2.0 | ACTIVE / IN FORCE", "success"),
    ]
    build_doc("POL-ORD-003_v2.0_Order-Intake-Approval-Backlog-Management.pdf",
              "CFO POLICY FRAMEWORK | CONTROLLED DOCUMENT", story)


# ---------------------------------------------------------------------------
# 7. WP-ORD-001 (Nov 2024 / FY2024 Q4)
# ---------------------------------------------------------------------------
def doc_wp001():
    story = [
        Paragraph("CFO POLICY FRAMEWORK", styles["Kicker"]),
        Paragraph("ORDER INTAKE RECOGNITION —<br/>PRIOR AUDIT PLAN &amp; TESTING SUMMARY", styles["DocTitle"]),
        Paragraph("Prior Audit Planner Output", styles["SubTitle"]),
        info_table([
            ["WORK PAPER ID", "WP-ORD-001", "AUDIT CYCLE", "FY2024 Q4"],
            ["DATE PREPARED", "November 2024", "POLICY TESTED", "POL-ORD-001 v1.0"],
            ["CONTROL ID", "CTRL-REV-014", "PROCESS AREA", "Order-to-Cash (O2C)"],
            ["PREPARED BY", "Internal Audit Team", "STATUS", "CLOSED — superseded Jan 2025"],
        ]),
        Spacer(1, 10),
        callout("SUPERSEDED", "Historical version retained for audit trail, prior-period testing and "
                              "control traceability.", "danger"),
        PageBreak(),

        Paragraph("1. Audit Objective", styles["H1"]),
        Paragraph("To assess whether Order Intake was recognized and measured in accordance with "
                  "POL-ORD-001 v1.0, and to evaluate the design and operating effectiveness of related "
                  "controls (CTRL-REV-014).", styles["Body"]),

        Paragraph("2. Background and Scope", styles["H1"]),
        Paragraph("This audit plan was developed for the FY2024 Q4 audit cycle, covering Order Intake "
                  "transactions booked between July 2024 and October 2024. Scope includes:", styles["Body"]),
        bullets(["Hardware/Software orders", "Standalone Services orders",
                 "Bundled multi-element arrangements"]),

        Paragraph("3. Key Risk Indicators (KRIs)", styles["H1"]),
        data_table(["KRI ID", "KRI Description", "Related Policy Clause", "Risk Rating"], [
            ["KRI-001", "Orders recognized without valid PO or contract", "Section 5.1", "High"],
            ["KRI-002", "Orders booked based on PO only, without countersigned contract", "Section 5.2",
             "Medium"],
            ["KRI-003", "Orders from low credit-rated customers booked without required sign-off",
             "Section 5.3.2", "High"],
            ["KRI-004", "Order Intake booked prior to satisfying timing criteria", "Section 5.4",
             "Medium"],
        ], col_widths=[0.8 * inch, 3.2 * inch, 1.3 * inch, 0.9 * inch]),

        Paragraph("4. Audit Planning Steps", styles["H1"]),
        Paragraph("4.1 Step Mapping to Policy Clauses", styles["H2"]),
        data_table(["Step #", "Audit Step Description", "Policy Clause Tested", "Related KRI"], [
            ["1", "Verify existence of valid PO for sampled orders", "5.1", "KRI-001"],
            ["2", "Confirm customer commitment evidenced by signed PO", "5.2", "KRI-002"],
            ["3", "Review credit rating classification and Finance Manager sign-off for orders rated "
                  "below B", "5.3.1, 5.3.2", "KRI-003"],
            ["4", "Confirm booking date aligns with PO receipt date", "5.4", "KRI-004"],
        ], col_widths=[0.6 * inch, 3.6 * inch, 1.2 * inch, 0.8 * inch]),

        Paragraph("4.2 Sample Selection Approach", styles["H2"]),
        bullets(["Population: All orders booked Jul–Oct 2024 (n = 342)",
                 "Sample size: 15 orders, judgmentally selected across 3 regions",
                 "Stratification: Weighted toward orders &gt;$50,000 and customers rated below B"]),

        Paragraph("5. Testing Procedures Performed", styles["H1"]),
        bullets(["Inspected PO documentation for existence and completeness",
                 "Traced credit rating classification to Group Credit Risk system",
                 "Recalculated booking date against PO receipt date per Section 5.4",
                 "Verified Finance Manager sign-off where credit rating below B"]),

        Paragraph("6. Findings Summary", styles["H1"]),
        data_table(["Step #", "Sample Size", "Exceptions Noted", "Exception Rate"], [
            ["1", "15", "0", "0%"],
            ["2", "15", "2", "13.3%"],
            ["3", "6", "1", "16.7%"],
            ["4", "15", "0", "0%"],
        ], col_widths=[0.9 * inch, 1.6 * inch, 1.8 * inch, 1.9 * inch]),
        Paragraph("Step 2: 2 orders were booked using PO only; no countersigned contract was on file at "
                  "time of booking. This was compliant under v1.0 but flagged as a forward-looking risk "
                  "given dual-document practice trends.", styles["Body"]),
        Paragraph("Step 3: 1 order from a customer rated C was booked without documented Finance Manager "
                  "sign-off. Root cause: sign-off obtained verbally, not recorded in system.", styles["Body"]),

        Paragraph("7. Prior Period Recommendations", styles["H1"]),
        bullets(["Introduce a secondary commitment document requirement beyond PO alone",
                 "Enhance credit risk assessment beyond single-factor credit rating to include payment "
                 "history and country risk",
                 "Formalize system-based sign-off workflow to eliminate verbal approval gaps"]),

        Paragraph("8. Forward-Looking Note for Next Cycle", styles["H1"]),
        Paragraph("Group Finance indicated a policy update to POL-ORD-001 was planned for Q1 2025, "
                  "expected to address the recommendations above. The next audit cycle should re-baseline "
                  "testing against the updated policy and re-assess KRI-002 and KRI-003 risk ratings.",
                  styles["Body"]),

        Paragraph("9. Revision History", styles["H1"]),
        data_table(["Version", "Date", "Summary of Change"], [
            ["1.0", "Nov 2024", "Initial work paper issuance"],
        ], col_widths=[0.9 * inch, 1.1 * inch, 4.6 * inch]),
        Spacer(1, 10),
        callout("CLOSED WORK PAPER", "WP-ORD-001 | FY2024 Q4", "danger"),
    ]
    build_doc("WP-ORD-Nov2024.pdf", "CFO POLICY FRAMEWORK | CONTROLLED DOCUMENT", story)


# ---------------------------------------------------------------------------
# 8. WP-ORD-002 (Feb 2025 / FY2025 Q1)
# ---------------------------------------------------------------------------
def doc_wp002():
    story = [
        Paragraph("CFO POLICY FRAMEWORK", styles["Kicker"]),
        Paragraph("ORDER INTAKE SSP ALLOCATION —<br/>PRIOR AUDIT PLAN &amp; TESTING SUMMARY", styles["DocTitle"]),
        Paragraph("Prior Audit Planner Output", styles["SubTitle"]),
        info_table([
            ["WORK PAPER ID", "WP-ORD-002", "AUDIT CYCLE", "FY2025 Q1"],
            ["DATE PREPARED", "February 2025", "POLICY TESTED", "POL-ORD-002 v1.0"],
            ["CONTROL ID", "CTRL-REV-015", "PROCESS AREA", "Order-to-Cash (O2C)"],
            ["PREPARED BY", "Internal Audit Team", "STATUS", "CLOSED — superseded Jun 2025"],
        ]),
        Spacer(1, 10),
        callout("SUPERSEDED", "Historical version retained for audit trail, prior-period testing and "
                              "control traceability.", "danger"),
        PageBreak(),

        Paragraph("1. Audit Objective", styles["H1"]),
        Paragraph("To assess whether SSP allocation for multi-element Order Intake arrangements was "
                  "performed in accordance with POL-ORD-002 v1.0 (Standalone List Price method), and to "
                  "evaluate control CTRL-REV-015.", styles["Body"]),

        Paragraph("2. Background and Scope", styles["H1"]),
        Paragraph("This audit plan covers multi-element contracts (HW/SW + Services) booked as Order "
                  "Intake between October 2024 and January 2025.", styles["Body"]),

        Paragraph("3. Key Risk Indicators (KRIs)", styles["H1"]),
        data_table(["KRI ID", "KRI Description", "Related Policy Clause", "Risk Rating"], [
            ["KRI-005", "SSP allocation not recalculated using approved list price method",
             "Section 5.1, 5.2", "High"],
            ["KRI-006", "Allocation variance &gt;20% booked without Finance Manager sign-off",
             "Section 7", "High"],
            ["KRI-007", "Incorrect deliverable categorization (HW/SW vs Services)", "Section 2",
             "Medium"],
        ], col_widths=[0.8 * inch, 3.3 * inch, 1.3 * inch, 0.8 * inch]),

        Paragraph("4. Audit Planning Steps", styles["H1"]),
        Paragraph("4.1 Step Mapping to Policy Clauses", styles["H2"]),
        data_table(["Step #", "Audit Step Description", "Policy Clause Tested", "Related KRI"], [
            ["1", "Recalculate SSP allocation using Standalone List Price formula", "5.2", "KRI-005"],
            ["2", "Compare recalculated allocation to booked system values", "5.2, 6", "KRI-005"],
            ["3", "Identify allocations with variance &gt;20% and confirm sign-off", "7", "KRI-006"],
            ["4", "Validate deliverable categorization against contract terms", "2", "KRI-007"],
        ], col_widths=[0.6 * inch, 3.6 * inch, 1.2 * inch, 0.8 * inch]),

        Paragraph("4.2 Sample Selection Approach", styles["H2"]),
        bullets(["Population: Multi-element contracts booked Oct 2024–Jan 2025 (n = 58)",
                 "Sample size: 10 contracts, judgmentally selected to include higher-value and "
                 "higher-variance arrangements"]),

        Paragraph("5. Testing Procedures Performed", styles["H1"]),
        bullets(["Obtained standard list price catalogue from Pricing Team",
                 "Recalculated SSP allocation using the approved formula",
                 "Compared recalculated allocation to system-booked values",
                 "For variances &gt;20%, traced to Finance Manager sign-off evidence"]),

        Paragraph("6. Findings Summary", styles["H1"]),
        Paragraph("6.1 Recalculation Results", styles["H2"]),
        data_table(["Contract ID", "Deliverable", "List Price", "Recalculated Allocation",
                    "Booked Allocation", "Variance"], [
            ["C-2041", "HW/SW", "30", "27.90", "27.90", "0%"],
            ["C-2041", "Services", "10", "3.10", "3.10", "0%"],
            ["C-2077", "HW/SW", "45", "38.25", "31.00", "-18.9%"],
            ["C-2077", "Services", "15", "12.75", "20.00", "+56.9%"],
        ], col_widths=[1.0 * inch, 1.0 * inch, 0.8 * inch, 1.4 * inch, 1.2 * inch, 0.9 * inch]),
        Paragraph("Overall: 8/10 contracts matched recalculation within tolerance; 2/10 exceeded the 20% "
                  "threshold.", styles["Body"]),
        Paragraph("Exception: Contract C-2077 showed a 56.9% variance on Services with no documented "
                  "Finance Manager sign-off, representing a control breach under Section 7.", styles["Body"]),

        Paragraph("7. Prior Period Recommendations", styles["H1"]),
        bullets(["Transition from unweighted Standalone List Price to a weighted allocation approach",
                 "Lower the sign-off variance threshold from 20% to a more conservative level",
                 "Implement system-enforced sign-off workflow"]),

        Paragraph("8. Forward-Looking Note for Next Cycle", styles["H1"]),
        Paragraph("Group Finance was expected to publish an updated SSP allocation methodology "
                  "introducing a Weighted Factor per deliverable category later in 2025. The next cycle "
                  "should re-baseline the recalculation approach using the new Relative SSP formula and "
                  "re-test the approval variance threshold.", styles["Body"]),

        Paragraph("9. Revision History", styles["H1"]),
        data_table(["Version", "Date", "Summary of Change"], [
            ["1.0", "Feb 2025", "Initial work paper issuance"],
        ], col_widths=[0.9 * inch, 1.1 * inch, 4.6 * inch]),
        Spacer(1, 10),
        callout("CLOSED WORK PAPER", "WP-ORD-002 | FY2025 Q1", "danger"),
    ]
    build_doc("WP-ORD-Feb2025.pdf", "CFO POLICY FRAMEWORK | CONTROLLED DOCUMENT", story)


# ---------------------------------------------------------------------------
# 9. WP-ORD-003 (Jun 2025 / FY2025 Q2)
# ---------------------------------------------------------------------------
def doc_wp003():
    story = [
        Paragraph("CFO POLICY FRAMEWORK", styles["Kicker"]),
        Paragraph("ORDER INTAKE APPROVAL &amp;<br/>BACKLOG MANAGEMENT — PRIOR<br/>"
                  "AUDIT PLAN &amp; TESTING SUMMARY", styles["DocTitle"]),
        Paragraph("Prior Audit Planner Output", styles["SubTitle"]),
        info_table([
            ["WORK PAPER ID", "WP-ORD-003", "AUDIT CYCLE", "FY2025 Q2"],
            ["DATE PREPARED", "June 2025", "POLICY TESTED", "POL-ORD-003 v1.0"],
            ["CONTROL ID", "CTRL-REV-016", "PROCESS AREA", "Order-to-Cash (O2C)"],
            ["PREPARED BY", "Internal Audit Team", "STATUS", "CLOSED — superseded Sep 2025"],
        ]),
        Spacer(1, 10),
        callout("SUPERSEDED", "Historical version retained for audit trail, prior-period testing and "
                              "control traceability.", "danger"),
        PageBreak(),

        Paragraph("1. Audit Objective", styles["H1"]),
        Paragraph("To assess compliance with the Order Intake Approval Authority Matrix and Order "
                  "Backlog monitoring requirements under POL-ORD-003 v1.0, and evaluate control "
                  "CTRL-REV-016.", styles["Body"]),

        Paragraph("2. Background and Scope", styles["H1"]),
        Paragraph("This audit plan covers orders booked between January 2025 and May 2025 for approval "
                  "matrix testing, and quarterly Backlog review reports for Q4 2024 and Q1 2025 for "
                  "aging testing.", styles["Body"]),

        Paragraph("3. Key Risk Indicators (KRIs)", styles["H1"]),
        data_table(["KRI ID", "KRI Description", "Related Policy Clause", "Risk Rating"], [
            ["KRI-008", "Orders approved by incorrect authority level relative to value", "Section 3",
             "High"],
            ["KRI-009", "Backlog items aging &gt;12 months not flagged for review", "Section 4.2, 4.3",
             "Medium"],
            ["KRI-010", "Quarterly Backlog review not evidenced/performed on schedule", "Section 4.1",
             "Medium"],
        ], col_widths=[0.8 * inch, 3.4 * inch, 1.3 * inch, 0.7 * inch]),

        Paragraph("4. Audit Planning Steps", styles["H1"]),
        Paragraph("4.1 Step Mapping to Policy Clauses", styles["H2"]),
        data_table(["Step #", "Audit Step Description", "Policy Clause Tested", "Related KRI"], [
            ["1", "Verify order approver matches required authority level relative to value tier", "3",
             "KRI-008"],
            ["2", "Recalculate Backlog aging and confirm items &gt;365 days were flagged", "4.2, 4.3",
             "KRI-009"],
            ["3", "Confirm quarterly Backlog review evidence exists for each quarter", "4.1", "KRI-010"],
        ], col_widths=[0.6 * inch, 3.6 * inch, 1.2 * inch, 0.8 * inch]),

        Paragraph("4.2 Sample Selection Approach", styles["H2"]),
        bullets(["Approval testing population: Orders booked Jan–May 2025 (n = 210)",
                 "Approval sample size: 20 orders, stratified across all 3 value tiers",
                 "Backlog testing: All items in Backlog &gt;300 days as of review date (n = 27), full "
                 "population tested"]),

        Paragraph("5. Testing Procedures Performed", styles["H1"]),
        bullets(["Traced order value to approver identity and role in system",
                 "Cross-referenced approver role against Table 1 (Delegation of Authority) in "
                 "POL-ORD-003 v1.0",
                 "Recalculated aging using Aging (Days) = Current Date − Original Order Booking Date",
                 "Confirmed items &gt;365 days were flagged and reviewed by Finance Manager",
                 "Obtained quarterly Backlog review sign-off evidence for Q4 2024 and Q1 2025"]),

        Paragraph("6. Findings Summary", styles["H1"]),
        Paragraph("6.1 Approval Matrix Testing", styles["H2"]),
        Paragraph("The supplied work paper excerpt ends after the testing procedures section; no "
                  "findings table or results for approval testing were included in the provided source "
                  "text.", styles["Body"]),
        Paragraph("6.2 Backlog Aging Testing", styles["H2"]),
        Paragraph("The supplied work paper excerpt does not include the subsequent findings, "
                  "recommendations, or revision-history content. Those sections have intentionally not "
                  "been invented.", styles["Body"]),

        Spacer(1, 10),
        callout("SOURCE COMPLETENESS NOTE",
                "This document has been formatted from the content provided. The source supplied for "
                "WP-ORD-003 ends at Section 6 and therefore the remaining original content is not "
                "reproduced.", "warning"),
    ]
    build_doc("WP-ORD-Jun2025.pdf", "CFO POLICY FRAMEWORK | CONTROLLED DOCUMENT", story)


if __name__ == "__main__":
    doc_pol001_v1()
    doc_pol001_v2()
    doc_pol002_v1()
    doc_pol002_v2()
    doc_pol003_v1()
    doc_pol003_v2()
    doc_wp001()
    doc_wp002()
    doc_wp003()
    print("\nAll 9 PDFs generated in:", OUT_DIR)
