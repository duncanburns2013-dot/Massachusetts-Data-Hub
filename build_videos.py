# -*- coding: utf-8 -*-
"""Build the Videos page from the 21 published YouTube cuts.

Two decisions worth recording.

Posters are served from this repo, not from i.ytimg.com. Twenty-one hot-linked
thumbnails would mean twenty-one requests to Google before anyone pressed play;
1.7 MB of local JPEG costs nothing against the 1 GB Pages ceiling and the page
stays a closed system until a visitor actually asks for a video.

The embed is a facade. Each tile is a real link to youtu.be, so it works with no
JavaScript at all; with JavaScript the click swaps in a youtube-nocookie iframe
in place. Twenty-one embedded players would pull megabytes of third-party script
and set cookies on arrival, which is the wrong trade on a site whose argument is
that it shows its working.
"""
import io, json, re, html, os

VIDEOS = [
 ('j5q_MkabqZI','parody',   'How Massachusetts Democrats actually work, staged as the meeting they would never hold.'),
 ('Opo_qFI7G_0','parody',   'An awards night for the 2025 Massachusetts Democratic Party, staged before the State of the State.'),
 ('guB1b7l0wMs','explainer','The gaslighting on utility bills, set against the law that put those charges on them.'),
 ('hlh5X6AnqEE','parody',   'A song about Elizabeth Warren and the lifelong habit of inventing the biography.'),
 ('BL8N9z6qPJg','parody',   'A musical about the places Massachusetts Democrats most like to expense their donors.'),
 ('p6GEJboVyQY','parody',   'A local X personality at the height of the migrant crisis, when Massachusetts led the news.'),
 ('J7Wv6-QoAL8','parody',   'They marched under No Kings, which reads oddly in a city that answers to a Queen.'),
 ('wclglGpNkHM','explainer','Following the money through the HHS mega-file release, one document at a time.'),
 ('khDK5GcUxKg','parody',   "The Governor's gaslighting, collected and played back against the record."),
 ('ulSCv2O5gLw','parody',   "One week of the Governor's own statements, rounded up and handed straight back."),
 ('pDAlm2HTaGY','explainer','Published reports on the crimes, set against the Massachusetts policy that let them out.'),
 ('AMpB4OEv5nI','explainer','Why people are leaving: labour force, migration, affordability and the jobs behind them.'),
 ('qerOCoYHwZk','explainer','For any politician claiming to be working on the cost of living here. They built it.'),
 ('ofgRUfMg6HI','explainer','Every charge on the bill traced back to the law it comes from. Nothing falls without repeal.'),
 ('iwyRVb5McCI','parody',   'Government by the Crown, performed in a Commonwealth that was meant to have abolished it.'),
 ('E7LFWvB3Ou0','parody',   'Massachusetts politics recast in Tolkien, with MassDems and the local X cast as themselves.'),
 ('0duhQMCQUlA','parody',   "Senator Jamie Eldridge's answer to Mass Fiscal, which needs very little commentary."),
 ('teLoDaZpZiI','parody',   'A song about Congressman James McGovern and the standards he keeps for everybody else.'),
 ('PMFi4Z4i6A0','parody',   'How a freshman representative landed a tier-one committee seat, and what that took.'),
 ('ZZejr_0D5cA','explainer','Massachusetts Democrats and the money that follows them, quoted from the record.'),
 ('nztB5Dhc2xw','explainer','A federal betrayal with state guardrails left unused, in a state near the top of the table.'),
 ('fxS8iVsaibY','parody',   'A parody of the friendly local-media interview, Jon Keller with Senator Paul Feeney.'),
]

META = {v['id']: v for v in json.load(io.open('build_videos_meta.json', encoding='utf-8-sig'))}

def mmss(s): return '%d:%02d' % (s // 60, s % 60)
def esc(t):  return html.escape(t, quote=True)

TILE = (
 '      <li class="vcard">\n'
 '        <a class="vthumb" href="https://youtu.be/{id}" data-id="{id}"\n'
 '           target="_blank" rel="noopener" aria-label="Play {t} ({dur})">\n'
 '          <img src="assets/video-thumbs/{id}.jpg" alt="" width="1280" height="720"'
 ' loading="{load}" fetchpriority="{prio}" decoding="async">\n'
 '          <span class="vplay" aria-hidden="true"></span>\n'
 '          <span class="vdur">{dur}</span>\n'
 '        </a>\n'
 '        <div class="vbody">\n'
 '          <span class="vkind vk-{k}">{kl}</span>\n'
 '          <h2 class="vname">{t}</h2>\n'
 '          <p class="vdesc">{d}</p>\n'
 '        </div>\n'
 '      </li>')

cards = []
for vid, kind, desc in VIDEOS:
    m = META[vid]
    assert os.path.exists('assets/video-thumbs/%s.jpg' % vid), vid
    # the first row is above the fold on every width we support, so those load
    # eagerly and at high priority; lazy-loading them only delays the LCP and
    # left them blank in a headless capture
    eager = len(cards) < 4
    cards.append(TILE.format(id=vid, t=esc(m['title']), dur=mmss(m['secs']),
                             k=kind, kl=kind.capitalize(), d=esc(desc),
                             load='eager' if eager else 'lazy',
                             prio='high' if eager else 'auto'))
GRID = '    <ul class="vgrid">\n' + '\n'.join(cards) + '\n    </ul>'

CSS = """
/* ---- the video wall ------------------------------------------------------
   Posters are local files, so nothing is requested from Google until a visitor
   presses play. Each tile is a real link to youtu.be and works with scripting
   off; the script upgrades it in place to a youtube-nocookie iframe. */
.vgrid{list-style:none;margin:26px 0 0;padding:0;display:grid;gap:22px;
  grid-template-columns:repeat(auto-fill,minmax(300px,1fr));grid-auto-rows:1fr}
.vcard{display:flex;flex-direction:column;height:100%;
  background:#fff;border:1px solid rgba(11,17,19,.07);border-radius:14px;
  overflow:hidden;box-shadow:0 1px 2px rgba(11,17,19,.05);
  transition:transform .35s cubic-bezier(.19,1,.22,1),box-shadow .35s}
.vcard:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(11,17,19,.13)}
.vthumb{position:relative;display:block;aspect-ratio:16/9;background:#0B1113;
  overflow:hidden;text-decoration:none}
.vthumb img{width:100%;height:100%;object-fit:cover;display:block}
.vthumb iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.vplay{position:absolute;left:50%;top:50%;width:58px;height:40px;margin:-20px 0 0 -29px;
  border-radius:10px;background:rgba(11,17,19,.62);
  transition:background .25s,transform .25s cubic-bezier(.19,1,.22,1)}
.vplay::after{content:"";position:absolute;left:23px;top:12px;border-style:solid;
  border-width:8px 0 8px 13px;border-color:transparent transparent transparent #fff}
.vthumb:hover .vplay,.vthumb:focus-visible .vplay{background:var(--cranberry);transform:scale(1.08)}
.vdur{position:absolute;right:8px;bottom:8px;padding:2px 6px;border-radius:4px;
  background:rgba(11,17,19,.78);color:#fff;
  font-family:var(--font-mono);font-size:11px;font-weight:600;letter-spacing:.02em}
.vbody{display:flex;flex-direction:column;flex:1;padding:14px 16px 16px}
.vkind{align-self:flex-start;font-family:var(--font-mono);font-size:11px;font-weight:700;
  letter-spacing:.14em;text-transform:uppercase;padding:3px 7px;border-radius:5px;border:1px solid}
.vk-parody{color:#7A2E10;border-color:rgba(194,65,12,.45);background:rgba(194,65,12,.09)}
.vk-explainer{color:#0F4577;border-color:rgba(20,85,143,.42);background:rgba(20,85,143,.09)}
.vname{font-family:var(--font-display);font-weight:700;font-size:17px;line-height:1.22;
  letter-spacing:-.015em;color:var(--ink);margin:10px 0 0}
.vdesc{margin:8px 0 0;font-family:var(--font-text);font-size:13.5px;line-height:1.5;
  color:var(--muted);flex:1}
/* The intro was set left in a full-width panel and read as a column stranded
   against the edge. Centred, on the same treatment as the Dashboards head. */
.doc-in{position:relative;overflow:hidden;text-align:center}
.doc-in::before{content:'';position:absolute;left:0;right:0;top:0;height:270px;
  pointer-events:none;z-index:0;
  background:radial-gradient(78% 120% at 6% 0%,rgba(104,10,29,.11),transparent 62%),
             radial-gradient(72% 120% at 94% 4%,rgba(20,85,143,.12),transparent 60%)}
.doc-in > *{position:relative;z-index:1}
.doc h1{justify-content:center;font-size:clamp(34px,5vw,72px)}
.doc .ramp{height:3px;margin:20px auto 26px;max-width:none}
.doc .panel-lede{font-size:clamp(17px,1.5vw,24px);line-height:1.45;
  max-width:none;margin-left:auto;margin-right:auto}
/* released to the panel width: nine centred lines became four. The measure
   is long for body copy, so the size and leading come up to carry it. */
.doc .panel-body{max-width:none;font-size:15px;line-height:1.72}
.doc .panel-note{max-width:none;font-size:13px;line-height:1.65}
.vgrid{text-align:left}
/* the two kinds, colour-keyed to the chips on every tile so the distinction is
   made before the grid starts rather than discovered inside it */
.k-par,.k-exp{font-style:normal;font-weight:700}
.k-par{color:#9A3412}
.k-exp{color:#0F4577}
@media (max-width:520px){ .vgrid{grid-template-columns:1fr} }
@media (prefers-reduced-motion: reduce){
  .vcard,.vplay{transition:none} .vcard:hover{transform:none}
}
"""

JS = """<script>
/* Upgrade a poster to the real player in place. The anchor already points at
   youtu.be, so with scripting off every tile still goes somewhere useful; this
   only intercepts the click when it can do better. youtube-nocookie keeps the
   request out of the ad cookie jar. */
(function(){
  var grid = document.querySelector('.vgrid');
  if (!grid) return;
  grid.addEventListener('click', function(e){
    var a = e.target.closest ? e.target.closest('.vthumb') : null;
    if (!a || a.dataset.playing) return;
    e.preventDefault();
    var f = document.createElement('iframe');
    f.src = 'https://www.youtube-nocookie.com/embed/' + a.dataset.id +
            '?autoplay=1&rel=0&modestbranding=1';
    f.title = a.getAttribute('aria-label') || 'Video';
    f.allow = 'accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture';
    f.allowFullscreen = true;
    a.dataset.playing = '1';
    a.innerHTML = '';
    a.appendChild(f);
  });
})();
</script>"""

# this file comes back from git and PowerShell as CRLF with a BOM, and the
# splice regexes below anchor on a bare newline
s = io.open('videos.html', encoding='utf-8-sig').read().replace('\r\n', '\n')

m = re.search(r'\s*<p class="panel-note" id="videos-note">.*?</p>\n', s, re.S)
assert m, 'placeholder note not found'
s = s[:m.start()] + '\n' + GRID + '\n' + '\n' + s[m.end():]

s = s.replace('<h1>Videos<i>6</i></h1>', '<h1>Videos<i>%d</i></h1>' % len(VIDEOS))
assert '<i>%d</i>' % len(VIDEOS) in s, 'count not updated'

OLD_LEDE = ('<p class="panel-lede">Short documentary and commentary pieces built from the\n'
            '    same sourced figures as the dashboards.</p>')
NEW_LEDE = '<p class="panel-lede">Short films on Massachusetts politics.\n    Some are <em class="k-par">parody</em>. Some are straight\n    <em class="k-exp">explainers</em>. Each one says which it is.</p>\n    <p class="panel-body">The parodies go after the Commonwealth&rsquo;s Democratic\n    establishment &mdash; Governor Healey, Mayor Wu and the legislators around them &mdash;\n    on corruption, hypocrisy, donor money expensed as a lifestyle, sanctuary policy\n    and the cost of living here. They are built from real news footage and real\n    figures cut against AI-generated montage, dark humour and staged confessionals.\n    The explainers carry no joke: the statute behind every line of a utility bill,\n    the labour-force and migration numbers behind the exodus, the HHS money trail,\n    the published reports behind the sanctuary argument, the H-1B filings. Where the\n    blame is bipartisan they say so &mdash; the H-1B film names the House and Senate of\n    both parties before it gets anywhere near Beacon Hill.</p>\n    <p class="panel-note">Every film is tagged Parody or Explainer, so nothing on this\n    page can be mistaken for the record. The explainers run on the same sourced\n    figures as the dashboards; the parodies are arguments, made in the open.</p>'

LEDE_TEXT = NEW_LEDE
assert s.count(OLD_LEDE) == 1, 'lede not found'
s = s.replace(OLD_LEDE, LEDE_TEXT)

# the page carries two <style> blocks - index's head styles and the doc styles
# added when this page was split out. The wall belongs with the doc styles.
assert s.count('</style>') == 2, s.count('</style>')
i = s.rindex('</style>')
s = s[:i] + CSS + '\n' + s[i:]
assert s.count('</body>') == 1
s = s.replace('</body>', JS + '\n</body>')


# Dashboards is an anchor on the front page, not on this one
s = s.replace('<a href="#dashboards">Dashboards</a>',
              '<a href="index.html#dashboards">Dashboards</a>')
assert '"#dashboards"' not in s, 'a bare #dashboards link survives'

io.open('videos.html', 'w', encoding='utf-8', newline='\n').write(s)

lens = [len(d) for _, _, d in VIDEOS]
print('videos       : %d  (parody %d, explainer %d)' % (len(VIDEOS),
      sum(1 for _, k, _ in VIDEOS if k == 'parody'),
      sum(1 for _, k, _ in VIDEOS if k == 'explainer')))
print('desc band    : %d-%d chars' % (min(lens), max(lens)))
print('total runtime: %s' % mmss(sum(META[v]['secs'] for v, _, _ in VIDEOS)))
print('page size    : %.1f KB' % (len(s) / 1024.0))
