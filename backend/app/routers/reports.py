from datetime import date, datetime
from html import escape
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import Asset, BIAAnalysis, Process, Risk, Treatment


router = APIRouter(
    prefix="/api/reports",
    tags=["Rapports"],
    dependencies=[Depends(get_current_user)],
)

NAVY = colors.HexColor("#14213D")
BLUE = colors.HexColor("#2563EB")
LIGHT_BLUE = colors.HexColor("#EAF1FB")
LIGHT_GREY = colors.HexColor("#F3F5F8")
DARK_GREY = colors.HexColor("#475569")
WHITE = colors.white

LEVELS = [
    (1, 4, "Faible"),
    (5, 9, "Moyen"),
    (10, 15, "Élevé"),
    (16, 25, "Critique"),
]


def risk_level(score: int) -> str:
    for minimum, maximum, label in LEVELS:
        if minimum <= score <= maximum:
            return label
    return "Non défini"


def bia_level(analysis: BIAAnalysis) -> tuple[int, str]:
    score = max(
        analysis.financial_impact,
        analysis.operational_impact,
        analysis.legal_impact,
        analysis.reputational_impact,
    )
    labels = {
        1: "Très faible",
        2: "Faible",
        3: "Moyen",
        4: "Élevé",
        5: "Critique",
    }
    return score, labels.get(score, "Non défini")


def safe(value) -> str:
    if value is None or value == "":
        return "—"
    return escape(str(value)).replace("\n", "<br/>")


def paragraph(value, style):
    return Paragraph(safe(value), style)


def make_table(data, widths, header=True):
    table = Table(
        data,
        colWidths=widths,
        repeatRows=1 if header else 0,
        hAlign="LEFT",
    )
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7DEE8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ])
        if len(data) > 1:
            commands.append(
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY])
            )
    table.setStyle(TableStyle(commands))
    return table


def add_section(story, title, styles):
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(title, styles["Section"]))
    story.append(Spacer(1, 2 * mm))


def page_header_footer(canvas, doc):
    canvas.saveState()
    width, height = landscape(A4)

    if doc.page > 1:
        canvas.setStrokeColor(colors.HexColor("#D7DEE8"))
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, height - 13 * mm, width - 15 * mm, height - 13 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(DARK_GREY)
        canvas.drawString(15 * mm, height - 10 * mm, "RiskMap-SMCA")
        canvas.drawRightString(
            width - 15 * mm,
            height - 10 * mm,
            "Rapport de gestion des risques et de continuité",
        )

    canvas.setStrokeColor(colors.HexColor("#D7DEE8"))
    canvas.line(15 * mm, 12 * mm, width - 15 * mm, 12 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(DARK_GREY)
    canvas.drawString(15 * mm, 8 * mm, "Document généré automatiquement")
    canvas.drawRightString(width - 15 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


@router.get("/smca/pdf", summary="Télécharger le rapport SMCA au format PDF")
def download_smca_report(
    process_ids: str | None = Query(
        default=None,
        description="IDs de processus séparés par des virgules (ex. 6,7,8,9). Vide = tout le rapport.",
    ),
    title: str | None = Query(
        default=None, max_length=120, description="Périmètre affiché sur la couverture"
    ),
    db: Session = Depends(get_db),
):
    try:
        ids = {int(x) for x in process_ids.split(",") if x.strip()} if process_ids else set()
    except ValueError:
        raise HTTPException(422, "process_ids doit être une liste d'entiers séparés par des virgules")
    processes = db.scalars(
        select(Process)
        .options(
            selectinload(Process.assets),
            selectinload(Process.bia_analysis),
            selectinload(Process.risks).selectinload(Risk.asset),
            selectinload(Process.risks).selectinload(Risk.treatments),
        )
        .order_by(Process.id)
    ).all()

    assets = db.scalars(
        select(Asset).options(selectinload(Asset.processes)).order_by(Asset.id)
    ).all()

    risks = db.scalars(
        select(Risk)
        .options(
            selectinload(Risk.process),
            selectinload(Risk.asset),
            selectinload(Risk.treatments),
        )
        .order_by(Risk.score.desc(), Risk.id)
    ).all()

    bia_analyses = db.scalars(
        select(BIAAnalysis)
        .options(selectinload(BIAAnalysis.process))
        .order_by(BIAAnalysis.id)
    ).all()

    treatments = db.scalars(
        select(Treatment)
        .options(
            selectinload(Treatment.risk).selectinload(Risk.process),
        )
        .order_by(Treatment.id)
    ).all()

    if ids:  # filtre par cas d'étude : on ne garde que les processus demandés et ce qui s'y rattache
        processes = [p for p in processes if p.id in ids]
        assets = [a for a in assets if any(p.id in ids for p in a.processes)]
        risks = [r for r in risks if r.process_id in ids]
        bia_analyses = [b for b in bia_analyses if b.process_id in ids]
        treatments = [t for t in treatments if t.risk and t.risk.process_id in ids]

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title="Rapport SMCA - RiskMap",
        author="RiskMap-SMCA",
        subject="Identification, analyse et traitement des risques",
    )

    base_styles = getSampleStyleSheet()
    styles = {
        "CoverTitle": ParagraphStyle(
            "CoverTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=29,
            leading=35,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8 * mm,
        ),
        "CoverSubtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base_styles["Normal"],
            fontSize=15,
            leading=21,
            textColor=DARK_GREY,
            alignment=TA_CENTER,
        ),
        "Section": ParagraphStyle(
            "Section",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=NAVY,
            spaceBefore=4 * mm,
            spaceAfter=3 * mm,
        ),
        "Subsection": ParagraphStyle(
            "Subsection",
            parent=base_styles["Heading3"],
            fontSize=11,
            leading=14,
            textColor=BLUE,
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base_styles["BodyText"],
            fontSize=9,
            leading=13,
            textColor=DARK_GREY,
            alignment=TA_LEFT,
            spaceAfter=3 * mm,
        ),
        "Cell": ParagraphStyle(
            "Cell",
            parent=base_styles["BodyText"],
            fontSize=7.5,
            leading=10,
            textColor=NAVY,
        ),
        "CellWhite": ParagraphStyle(
            "CellWhite",
            parent=base_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=WHITE,
        ),
        "Small": ParagraphStyle(
            "Small",
            parent=base_styles["BodyText"],
            fontSize=8,
            leading=11,
            textColor=DARK_GREY,
        ),
    }

    def cell(value, white=False):
        return paragraph(value, styles["CellWhite"] if white else styles["Cell"])

    story = []

    # COUVERTURE
    story.extend([
        Spacer(1, 28 * mm),
        Paragraph("RiskMap-SMCA", styles["CoverTitle"]),
        Paragraph(
            "Rapport de gestion des risques et d'analyse d'impact métier",
            styles["CoverSubtitle"],
        ),
        Spacer(1, 12 * mm),
    ])

    cover_data = [
        [cell("PÉRIMÈTRE", True), cell("RÉFÉRENTIELS", True), cell("DATE DE GÉNÉRATION", True)],
        [
            cell(title or "Identification et cartographie des risques liés à la continuité d'activité"),
            cell("ISO 22301 · ISO 31000"),
            cell(datetime.now().strftime("%d/%m/%Y à %H:%M")),
        ],
    ]
    cover_table = make_table(cover_data, [85 * mm, 65 * mm, 75 * mm])
    story.extend([cover_table, Spacer(1, 12 * mm)])
    story.append(Paragraph(
        "Ce document présente un état des données enregistrées dans RiskMap-SMCA "
        "à la date de génération. Il constitue un support d'aide à l'analyse et "
        "à la préparation de la continuité d'activité.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "Référentiels méthodologiques : ISO 22301 pour le management de la "
        "continuité d'activité et ISO 31000 pour le management du risque. "
        "Ce rapport ne constitue ni une certification ni une attestation de conformité.",
        styles["Small"],
    ))
    story.append(PageBreak())

    # SYNTHÈSE
    add_section(story, "1. Synthèse générale", styles)
    critical_risks = sum(1 for risk in risks if risk_level(risk.score) == "Critique")
    high_risks = sum(1 for risk in risks if risk_level(risk.score) == "Élevé")
    bia_critical = sum(1 for item in bia_analyses if bia_level(item)[0] == 5)
    bia_high = sum(1 for item in bia_analyses if bia_level(item)[0] == 4)

    summary_data = [
        [cell("Indicateur", True), cell("Valeur", True)],
        [cell("Processus métier"), cell(len(processes))],
        [cell("Actifs recensés"), cell(len(assets))],
        [cell("Risques identifiés"), cell(len(risks))],
        [cell("Risques critiques"), cell(critical_risks)],
        [cell("Risques élevés"), cell(high_risks)],
        [cell("Analyses BIA réalisées"), cell(len(bia_analyses))],
        [cell("BIA critiques"), cell(bia_critical)],
        [cell("BIA élevées"), cell(bia_high)],
        [cell("Plans de traitement"), cell(len(treatments))],
    ]
    story.append(make_table(summary_data, [100 * mm, 40 * mm]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "La criticité d'un risque est calculée selon la formule : "
        "<b>Probabilité × Impact</b>, sur une échelle de 1 à 25. "
        "La criticité BIA présentée dans ce rapport correspond au maximum "
        "des impacts financier, opérationnel, juridique et réputationnel.",
        styles["Body"],
    ))

    # PÉRIMÈTRE ET MÉTHODE
    add_section(story, "2. Périmètre et méthode", styles)
    story.append(Paragraph(
        "La démarche consiste à recenser les processus métier, identifier les "
        "actifs qui les supportent, analyser les conséquences d'une interruption "
        "et évaluer les risques susceptibles d'affecter la continuité des activités.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "<b>Analyse BIA :</b> évaluation des impacts financiers, opérationnels, "
        "juridiques et réputationnels. Les objectifs MTPD, RTO et RPO sont repris "
        "lorsqu'ils sont renseignés dans la fiche du processus.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "<b>Évaluation des risques :</b> chaque risque est évalué selon une "
        "probabilité et un impact de 1 à 5. Le score obtenu détermine le niveau "
        "Faible (1–4), Moyen (5–9), Élevé (10–15) ou Critique (16–25).",
        styles["Body"],
    ))

    # PROCESSUS
    add_section(story, "3. Registre des processus métier", styles)
    process_data = [[
        cell("Processus", True), cell("Description", True),
        cell("Criticité", True), cell("MTPD (h)", True),
        cell("RTO (h)", True), cell("RPO (min)", True),
        cell("Actifs associés", True),
    ]]
    for process in processes:
        process_data.append([
            cell(process.name),
            cell(process.description),
            cell(process.criticality),
            cell(process.mtpd_hours),
            cell(process.rto_hours),
            cell(process.rpo_minutes),
            cell(", ".join(asset.name for asset in process.assets)),
        ])
    if not processes:
        process_data.append([cell("Aucun processus enregistré")] + [cell("—")] * 6)
    story.append(make_table(
        process_data,
        [42 * mm, 58 * mm, 20 * mm, 22 * mm, 20 * mm, 22 * mm, 55 * mm],
    ))

    # ACTIFS
    add_section(story, "4. Inventaire des actifs", styles)
    asset_data = [[
        cell("Actif", True), cell("Type", True),
        cell("Description", True), cell("Processus associés", True),
    ]]
    for asset in assets:
        asset_data.append([
            cell(asset.name),
            cell(asset.asset_type),
            cell(asset.description),
            cell(", ".join(process.name for process in asset.processes)),
        ])
    if not assets:
        asset_data.append([cell("Aucun actif enregistré")] + [cell("—")] * 3)
    story.append(make_table(
        asset_data,
        [48 * mm, 35 * mm, 85 * mm, 70 * mm],
    ))

    # BIA
    add_section(story, "5. Analyse d'impact métier (BIA)", styles)
    bia_data = [[
        cell("Processus", True), cell("Financier", True),
        cell("Opérationnel", True), cell("Juridique", True),
        cell("Réputationnel", True), cell("Niveau global", True),
    ]]
    for analysis in bia_analyses:
        score, label = bia_level(analysis)
        bia_data.append([
            cell(analysis.process.name if analysis.process else "—"),
            cell(analysis.financial_impact),
            cell(analysis.operational_impact),
            cell(analysis.legal_impact),
            cell(analysis.reputational_impact),
            cell(f"{label} ({score}/5)"),
        ])
    if not bia_analyses:
        bia_data.append([cell("Aucune analyse BIA enregistrée")] + [cell("—")] * 5)
    story.append(make_table(
        bia_data,
        [65 * mm, 30 * mm, 35 * mm, 30 * mm, 35 * mm, 45 * mm],
    ))

    for analysis in bia_analyses:
        process_name = analysis.process.name if analysis.process else "Processus"
        story.append(Paragraph(f"Conséquences et ressources — {safe(process_name)}", styles["Subsection"]))
        story.append(Paragraph(
            f"<b>Conséquences métier :</b> {safe(analysis.business_consequences)}",
            styles["Body"],
        ))
        story.append(Paragraph(
            f"<b>Ressources essentielles :</b> {safe(analysis.essential_resources)}",
            styles["Body"],
        ))

    # RISQUES
    add_section(story, "6. Cartographie des risques", styles)
    risk_data = [[
        cell("Processus", True), cell("Menace", True),
        cell("Vulnérabilité", True), cell("Actif", True),
        cell("P", True), cell("I", True),
        cell("Score", True), cell("Niveau", True),
    ]]
    for risk in risks:
        risk_data.append([
            cell(risk.process.name if risk.process else "—"),
            cell(risk.threat),
            cell(risk.vulnerability),
            cell(risk.asset.name if risk.asset else "—"),
            cell(risk.probability),
            cell(risk.impact),
            cell(risk.score),
            cell(risk_level(risk.score)),
        ])
    if not risks:
        risk_data.append([cell("Aucun risque enregistré")] + [cell("—")] * 7)
    story.append(make_table(
        risk_data,
        [35 * mm, 48 * mm, 48 * mm, 38 * mm, 12 * mm, 12 * mm, 16 * mm, 25 * mm],
    ))

    # MATRICE 5 x 5
    story.append(Paragraph("Matrice de criticité (Probabilité × Impact)", styles["Subsection"]))
    matrix_data = [[
        cell("P \\ I", True),
        cell("1", True), cell("2", True), cell("3", True),
        cell("4", True), cell("5", True),
    ]]
    for probability in range(5, 0, -1):
        row = [cell(probability, True)]
        for impact in range(1, 6):
            score = probability * impact
            count = sum(
                1 for risk in risks
                if risk.probability == probability and risk.impact == impact
            )
            row.append(Paragraph(
                f"<b>{score}</b><br/><font size='7'>{count} risque(s)</font>",
                styles["Cell"],
            ))
        matrix_data.append(row)
    matrix_table = make_table(
        matrix_data,
        [25 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm],
    )
    matrix_table.setStyle(TableStyle([
        ("BACKGROUND", (1, 1), (-1, -1), LIGHT_BLUE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(matrix_table)
    story.append(Paragraph(
        "Chaque cellule indique le score P × I et le nombre de risques "
        "enregistrés pour cette combinaison.",
        styles["Small"],
    ))

    # TRAITEMENTS
    story.append(PageBreak())
    add_section(story, "7. Plans de traitement des risques", styles)
    treatment_data = [[
        cell("Risque / processus", True), cell("Stratégie", True),
        cell("Action prévue", True), cell("Responsable", True),
        cell("Échéance", True), cell("Statut", True),
        cell("Risque résiduel", True),
    ]]
    for treatment in treatments:
        risk = treatment.risk
        residual = "—"
        if treatment.residual_probability is not None and treatment.residual_impact is not None:
            residual_score = treatment.residual_probability * treatment.residual_impact
            residual = f"{residual_score} ({risk_level(residual_score)})"

        risk_label = "—"
        if risk:
            process_name = risk.process.name if risk.process else "Processus"
            risk_label = f"{risk.threat} / {process_name}"

        due = treatment.due_date.strftime("%d/%m/%Y") if treatment.due_date else "—"
        treatment_data.append([
            cell(risk_label),
            cell(treatment.strategy),
            cell(treatment.action),
            cell(treatment.owner),
            cell(due),
            cell(treatment.status),
            cell(residual),
        ])
    if not treatments:
        treatment_data.append([cell("Aucun traitement enregistré")] + [cell("—")] * 6)
    story.append(make_table(
        treatment_data,
        [42 * mm, 25 * mm, 70 * mm, 32 * mm, 25 * mm, 25 * mm, 30 * mm],
    ))

    # RECOMMANDATIONS
    add_section(story, "8. Synthèse et recommandations", styles)
    recommendations = [
        "Prioriser le traitement des risques classés Critiques et Élevés.",
        "Définir et valider les objectifs de reprise RTO et RPO pour chaque processus critique.",
        "Vérifier régulièrement l'efficacité des mesures de traitement et documenter les risques résiduels.",
        "Tester les procédures de sauvegarde, de restauration et de continuité.",
        "Mettre à jour les analyses BIA et le registre des risques lors de tout changement important.",
        "Prévoir des exercices périodiques et conserver les preuves des résultats obtenus.",
    ]
    for recommendation in recommendations:
        story.append(Paragraph(f"• {safe(recommendation)}", styles["Body"]))

    add_section(story, "9. Conclusion", styles)
    story.append(Paragraph(
        "RiskMap-SMCA centralise les informations relatives aux processus métier, "
        "aux actifs, aux analyses d'impact et aux risques. Ce rapport fournit une "
        "photographie des données disponibles au moment de son édition. Il doit "
        "être complété par la validation métier, la définition des stratégies de "
        "continuité, la formalisation des procédures PCA et la réalisation "
        "d'exercices réguliers.",
        styles["Body"],
    ))

    document.build(
        story,
        onFirstPage=page_header_footer,
        onLaterPages=page_header_footer,
    )

    buffer.seek(0)
    suffix = "_p" + "-".join(str(i) for i in sorted(ids)) if ids else ""
    filename = f"rapport_smca{suffix}_{date.today().isoformat()}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
