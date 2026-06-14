"""
PDF Parser Module — Extraction de texte depuis des fichiers PDF.

Utilise pdfplumber pour une extraction haute fidélité qui préserve
la structure du document (tableaux, colonnes, listes).
"""

import pdfplumber
import re
from pathlib import Path
from typing import Optional


class PDFParser:
    """Extracteur de texte PDF haute qualité."""

    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extrait le texte complet d'un fichier PDF.

        Args:
            file_path: Chemin vers le fichier PDF.

        Returns:
            Texte extrait, nettoyé et normalisé.

        Raises:
            FileNotFoundError: Si le fichier n'existe pas.
            ValueError: Si le fichier n'est pas un PDF valide.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Format non supporté: {path.suffix}. Seul le PDF est accepté.")

        full_text = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extraction du texte principal
                    text = page.extract_text(
                        x_tolerance=2,
                        y_tolerance=2
                    )
                    if text:
                        full_text.append(text)

                    # Extraction des tableaux (souvent présents dans les CV)
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row:
                                cells = [str(cell).strip() for cell in row if cell]
                                if cells:
                                    full_text.append(" | ".join(cells))

        except Exception as e:
            raise ValueError(f"Erreur lors de la lecture du PDF: {str(e)}")

        raw_text = "\n".join(full_text)
        return PDFParser._clean_text(raw_text)

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Nettoie et normalise le texte extrait.

        - Supprime les caractères de contrôle
        - Normalise les espaces et sauts de ligne
        - Préserve la structure (listes, paragraphes)
        """
        # Supprimer les caractères de contrôle (sauf newline et tab)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # Normaliser les espaces multiples (mais pas les newlines)
        text = re.sub(r'[^\S\n]+', ' ', text)

        # Normaliser les sauts de ligne multiples (max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Supprimer les espaces en début/fin de chaque ligne
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()

    @staticmethod
    def extract_sections(text: str) -> dict:
        """
        Tente de détecter les sections principales d'un CV.

        Retourne un dictionnaire avec les sections identifiées :
        - experience, education, skills, languages, certifications, etc.
        """
        section_patterns = {
            'experience': r'(?i)(exp[ée]rience[s]?\s*(professionnelle[s]?)?|work\s*experience|professional\s*experience|parcours\s*professionnel)',
            'education': r'(?i)(formation[s]?|education|[ée]tudes|diplômes?|academic|cursus)',
            'skills': r'(?i)(comp[ée]tence[s]?|skills?|technologies?|technical\s*skills?|savoir[\s-]*faire)',
            'languages': r'(?i)(langue[s]?|languages?|linguistique)',
            'certifications': r'(?i)(certification[s]?|certifi[ée][s]?|accréditation[s]?)',
            'projects': r'(?i)(projet[s]?|projects?|réalisation[s]?|portfolio)',
            'summary': r'(?i)(profil|summary|résumé|about|à propos|objectif|présentation)',
            'interests': r'(?i)(intérêts?|interests?|hobbies?|loisirs?|centres?\s*d\'intérêt)',
        }

        sections = {}
        lines = text.split('\n')
        current_section = 'header'
        current_content = []

        for line in lines:
            matched = False
            for section_name, pattern in section_patterns.items():
                if re.search(pattern, line) and len(line.strip()) < 80:
                    # Sauvegarder la section précédente
                    if current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = section_name
                    current_content = []
                    matched = True
                    break

            if not matched:
                current_content.append(line)

        # Sauvegarder la dernière section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections
