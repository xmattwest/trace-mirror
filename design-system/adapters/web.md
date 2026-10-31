# Web and applications

## Purpose and structure

Choose Read, Explain, Operate, Persuade, or Experience per surface. An app's landing page can be Persuade while its dashboard is Operate. Start with the actual task and content.

For informational pages, compose an overview before exposing the full reference. Lead with the takeaway, explain relationships or decisions visually when useful, and finish with a short next-step sequence. Keep copy concise; move implementation details, receipts, and supporting sources into a disclosure or linked reference. Record what the overview merged or relocated. A file conversion alone does not complete this design work.

Choose the opening from the reader's task. A tool page can begin with its name, what it reads, and a working launch command; a visual explorer can begin with the artifact and its controls; a research page can begin with the question and result. Use a plain descriptive title by default. Large display type is an explicit, content-led choice, such as a distinctive persona or a consequential result. Let line breaks follow the reading measure unless a deliberate break improves meaning.

## Type and layout

Use the profile's web ramp. Prose measure defaults to about 66 characters. Body is 18 px for reading, 16 px for compact UI; supporting text is 14 px by default. The ramp has a real middle: kicker 12 px, lede 20 px, section heading 30 px, page heading 40 px, display 52 px. Rem units and user zoom must work. Display moments can be fluid; task UI uses a restrained fixed scale.

Semantic `h1` does not imply display styling. The handbook's ordinary heading default uses the profile's heading family, weight, and web heading scale. `.display-title` and explicitly composed display surfaces opt into the Newsreader display scale. Kickers use the profile's kicker role and mono stack, uppercase with wide tracking — they orient, never decorate. The lede holds a fixed ratio to body (20/18). `.page-intro` provides a compact informational opening.

Balance long headings only on display surfaces; ordinary headings wrap naturally. Tables and data set tabular numerals.

Use the 4 px spacing base, a responsive max-width container, and at least 24 px mobile gutters. These replace a universal percentage margin. Let tables be appropriately dense. Collapse columns structurally at narrow widths; do not shrink labels until the whole desktop layout fits.

## Components and behavior

Use flat surfaces, selective outlines, and grouping by proximity. Containers are useful when they group meaningful content, not around every paragraph. Primary controls use Blue Slate with Ivory text, or orange with Onyx text and an essential dark boundary.

Provide relevant default, hover, focus, selected, disabled, loading, empty, error, and success states. Labels communicate state independently of color. Use native controls and familiar navigation; support keyboard operation, visible focus, descriptive links, and a skip link. Prefer 44 px comfortable touch targets; verify the applicable accessibility standard rather than treating that comfort target as the WCAG minimum.

## Motion and review

Motion explains state and feedback. Use the profile's short transition duration and complete static content under reduced motion. Avoid delayed page-load choreography in tools.

Inspect desktop, phone, and 200% zoom; check real copy, long strings, focus, error recovery, touch targets, and local diagram scrolling. No page-wide horizontal overflow. See `charts.md` for a figure's independent minimum readable width.
