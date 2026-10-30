# Translation Style Guide

This style guide applies to all translations of the biblioteq-web user interface. It is intended for both human translators and AI translation systems. Follow these guidelines to keep the interface clear, consistent, and suitable for a library catalog used by patrons and staff.

Source language: English.  
Primary audience: people searching and browsing a BiblioteQ library collection (books, media, journals, and other materials) in a home, school, or small-to-medium organizational setting.  
Product: biblioteq-web — a read-only web browser for BiblioteQ collections.

## Voice and Tone

- **Clear and direct.** Use plain language that is easy to understand. Prefer short, concrete words over long or abstract ones.
- **Neutral and professional.** The interface should feel reliable and helpful, like a well-designed library catalog. Avoid slang, humor, marketing language, or overly casual phrasing. Also avoid stiff or bureaucratic wording.
- **Helpful, not instructional.** The UI mostly labels things and reports status. Do not add extra explanations or instructions unless the source string does.
- **Consistent.** Use the same term for the same concept everywhere. Prefer the established library or technical term over a creative synonym.

## Do Not Translate

Leave the following unchanged (copy them exactly):

- Product and software names: `BiblioteQ`, `biblioteq-web`
- Standard identifiers and codes: ISBN-10, ISBN-13, ISSN, UPC, barcode values, catalogue numbers, call numbers, LC control numbers, Dewey numbers, accession numbers, document IDs, job numbers
- Technical placeholders and format markers: `%(page)s`, `%(pages)s`, `%(count)s`, `%(name)s`, `%(title)s`, `%(query)s`, `%(available)s`, `%(total)s`, `%(label)s`, and any similar `%(name)s` or `{name}` style placeholders
- HTML entities and structural markup that appear in source strings
- File extensions, URL paths, and code identifiers
- Proper names of people, places, or organizations that appear as data (these usually come from the database and are not in the UI strings)

When a string contains a placeholder, translate the surrounding text and keep the placeholder exactly as written, including the parentheses and letter.

## Placeholders and Plural Forms

This project uses gettext. Many strings contain named placeholders and some use plural forms.

- Preserve every placeholder exactly (`%(count)s`, `%(title)s`, etc.). Do not rename, reorder the name, or change the format.
- For plural strings (`msgid` / `msgid_plural`), provide the correct plural form(s) for your language. Do not force the English two-form pattern if your language has a different number of plurals.
- Keep the meaning of the count or value that the placeholder represents. Example: “%(count)s copies owned” must still express ownership of that number of copies.

## Context (msgctxt)

Many strings have a message context that disambiguates meaning. Always read the context before translating:

- `item-type` — singular and plural names of catalog item types (Book / Books, DVD / DVDs, Music CD / Music CDs, Journal / Journals, Magazine / Magazines, Video Game / Video Games, Grey Literature, Photograph Collection / Photograph Collections)
- `tab-book`, `tab-dvd`, `tab-cd`, `tab-journal`, `tab-magazine`, `tab-videogame`, `tab-greyliterature`, `tab-photograph`, `tab-default` — labels for tabs on item detail pages (Main, Holdings, Details, Notes)
- `placeholder` — text shown inside an empty search field
- `aria-label` — accessible names for screen readers (must describe the control clearly)
- `button` — text on a button

When the same English word appears with different contexts, the translations may differ.

## Terminology

Use consistent, standard library terminology. Prefer terms already established in the parent BiblioteQ project or in common library practice for your language.

| English | Guidance |
| --- | --- |
| Book / Books | Standard library term for monographs |
| DVD / DVDs | Keep “DVD” as the acronym; translate the surrounding word if needed |
| Music CD / Music CDs | Prefer the common term for audio compact discs |
| Journal / Journals | Scholarly or serial publications |
| Magazine / Magazines | Popular periodicals |
| Video Game / Video Games | Standard term |
| Grey Literature | Keep the established library science term; do not invent a new phrase |
| Photograph Collection / Photograph Collections | Collections of photographs |
| ISBN-13, ISBN-10, ISSN, UPC | Leave the acronyms; translate only if your language has a widely used full form that is still recognizable |
| Call Number | Standard library term (shelf mark / classification number) |
| Dewey Class Number / Dewey Number | Prefer the established name for the Dewey Decimal Classification number |
| Location | Physical or logical location of the item in the collection |
| Availability / Available | Whether copies can be borrowed |
| Copies owned / checked out | Holdings status |
| Recently added | Items added most recently |
| All types / All locations | Filters meaning “no restriction” |
| Unknown location / Unknown | Items that have no location recorded |

If a better established term exists in your language’s library community, use it consistently and note it in a comment on Crowdin so others can follow it.

## UI Constraints

- Buttons, navigation links, tab labels, and filter options must stay short. Prefer the shortest clear translation.
- Search placeholders and aria-labels should remain concise.
- Page titles and headings can be slightly longer if needed for clarity.
- Avoid adding punctuation that is not in the source unless it is required by your language’s orthography.
- Match the capitalization style of the source where it is conventional in your language (title case for headings and buttons is common in English; many languages use sentence case).

## Accessibility

Strings marked with the `aria-label` context are read by screen readers. Translate them so a user who cannot see the screen understands what the control is for. Do not omit words that convey the purpose.

## Numbers, Dates, and Units

- Do not change the format of placeholders that represent numbers.
- Currency units and monetary values come from the database; UI strings only label the field (“Price”, “Monetary Units”).
- Runtime, length, and similar measurements should use the natural phrasing of your language.

## What to Do When Unsure

- Look at the surrounding English string and any message context.
- Prefer a clear, slightly longer translation over an ambiguous short one for body text; prefer brevity for buttons and navigation.
- Leave a comment on the string in Crowdin if you had to make a judgment call or if a term needs discussion.
- Do not invent new UI concepts or add marketing language.

## Examples

**Source:** `%(count)s copies owned`  
**Good:** Keep the placeholder and express the same meaning with the correct plural form for your language.  
**Avoid:** Translating the placeholder name or dropping the number.

**Source (context `aria-label`):** `Search`  
**Good:** A clear accessible name such as “Search the collection” or the natural equivalent.  
**Avoid:** A single word that could mean “research” or “look up” in a different sense.

**Source (context `item-type`):** `Grey Literature`  
**Good:** The standard library term used in your language.  
**Avoid:** A literal word-for-word rendering that does not match local library usage.

## Related Resources

- Localization workflow: [docs/localization.md](localization.md)
- Crowdin project: https://crowdin.com/project/biblioteq-web
- Source catalog: `app/locales/messages.pot`
- Item type and field labels: `app/item_types.py`

---

*Last updated: 2026-10-30. This guide may be revised as the interface grows. Suggestions are welcome via the GitHub repository.*
