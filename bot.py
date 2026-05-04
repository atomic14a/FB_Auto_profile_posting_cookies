#!/usr/bin/env python3
"""
FB Auto Profile Poster v2.0
Pure Python • requests + GraphQL • No Selenium
"""

import time, random, os, re, json, html as html_mod, atexit, signal
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote as url_quote
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.table import Table
from rich import box

console = Console()

# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_cookies(s):
    d = {}
    for item in s.strip().split(';'):
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            d[k.strip()] = v.strip()
    return d

def get_session(cookies):
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    s.mount('https://', HTTPAdapter(max_retries=retries))
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    })
    s.cookies.update(cookies)
    return s

def extract_tokens(page_text):
    tokens = {}
    for p in [r'"dtsg":"([^"]+)"', r'"dtsg":\{"token":"([^"]+)"\}',
              r'\["DTSGInitialData",\[\],\{"token":"([^"]+)"',
              r'name="fb_dtsg" value="([^"]+)"']:
        m = re.search(p, page_text)
        if m:
            tokens['fb_dtsg'] = html_mod.unescape(m.group(1))
            break
    for p in [r'"sprinkleValue":"([^"]+)"', r'name="jazoest" value="([^"]+)"']:
        m = re.search(p, page_text)
        if m:
            tokens['jazoest'] = m.group(1)
            break
    m = re.search(r'"lsd":"([^"]+)"', page_text)
    if m and m.group(1) != 'null':
        tokens['lsd'] = m.group(1)
    m = re.search(r'"server_revision":(\d+)', page_text)
    if m:
        tokens['__rev'] = m.group(1)
    m = re.search(r'"haste_session":"([^"]+)"', page_text)
    if m:
        tokens['__hs'] = m.group(1)
    # Try to find access token
    for p in [r'"accessToken":"(EAA[A-Za-z0-9]+)"', r'"access_token":"(EAA[A-Za-z0-9]+)"']:
        m = re.search(p, page_text)
        if m:
            tokens['access_token'] = m.group(1)
            break
    return tokens

def display_banner():
    b = Text()
    b.append("╔════════════════════════════════════════════════════╗\n", style="bold cyan")
    b.append("║        ", style="bold cyan")
    b.append("FB AUTO PROFILE POSTER", style="bold white")
    b.append("  v2.0        ║\n", style="bold cyan")
    b.append("║    ", style="bold cyan")
    b.append("Pure Python • GraphQL • Bulk Posting", style="dim white")
    b.append("     ║\n", style="bold cyan")
    b.append("╚════════════════════════════════════════════════════╝", style="bold cyan")
    console.print(Panel(b, border_style="bright_blue", box=box.DOUBLE))


# ─── Core Bot ────────────────────────────────────────────────────────────────

class FacebookPoster:

    def __init__(self, cookie_str):
        self.raw_cookies = cookie_str
        self.cookies = parse_cookies(cookie_str)
        self.session = get_session(self.cookies)
        self.c_user = self.cookies.get('c_user')
        self.i_user = self.cookies.get('i_user')
        self.user_name = None
        self.tokens = {}

    @property
    def target_id(self):
        return self.i_user or self.c_user

    @property
    def is_page(self):
        return self.i_user is not None

    def validate_session(self):
        console.print("\n[bold yellow]🔐 Validating Session...[/bold yellow]")
        try:
            if not self.c_user:
                console.print("[bold red]  ✖ No c_user cookie found[/bold red]")
                return False

            # Step 1: Check m.facebook.com
            resp = self.session.get("https://m.facebook.com/home.php", timeout=30, allow_redirects=True)
            url_l = resp.url.lower()
            if '/checkpoint/' in url_l:
                console.print("[bold red]  ✖ ACCOUNT CHECKPOINTED[/bold red]")
                return False
            if '/login' in url_l and '/home' not in url_l:
                console.print("[bold red]  ✖ COOKIES EXPIRED[/bold red]")
                return False

            title_m = re.search(r'<title>(.*?)</title>', resp.text, re.I)
            title = title_m.group(1) if title_m else ""
            if 'Log in' in title or 'Log into' in title:
                console.print("[bold red]  ✖ COOKIES EXPIRED[/bold red]")
                return False

            # Step 2: Extract tokens from this page
            self.tokens = extract_tokens(resp.text)

            # Step 3: Get profile name via www.facebook.com (desktop UA)
            time.sleep(random.uniform(1, 2))
            desktop_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            }
            p_resp = self.session.get(
                f"https://www.facebook.com/profile.php?id={self.c_user}",
                timeout=30, allow_redirects=True, headers=desktop_headers)

            # Try title
            nm = re.search(r'<title>(.*?)</title>', p_resp.text, re.I)
            if nm:
                name = nm.group(1).strip()
                # Strip notification counts and Facebook suffix
                name = re.sub(r'^\(\d+\+?\)\s*', '', name)
                for sfx in [' | Facebook', ' - Facebook', '| Facebook']:
                    name = name.replace(sfx, '').strip()
                if name and name.lower() not in ('facebook', 'error', ''):
                    self.user_name = name

            # Fallback: try patterns in page JS
            if not self.user_name:
                for p in [r'og:title" content="([^"]+)"',
                          r'"ownerName":"([^"]+)"',
                          r'"name":"([^"]+)","id":"' + self.c_user + '"',
                          r'"profileName":"([^"]+)"']:
                    m = re.search(p, p_resp.text)
                    if m:
                        name = m.group(1).strip()
                        if name and name.lower() not in ('facebook', 'error'):
                            self.user_name = name
                            break

            # Only add tokens that are missing (DON'T overwrite m.facebook.com fb_dtsg)
            www_tokens = extract_tokens(p_resp.text)
            for k, v in www_tokens.items():
                if k not in self.tokens:
                    self.tokens[k] = v

            if not self.user_name:
                self.user_name = f"User {self.c_user}"

            console.print(f"[bold green]  ✔ Logged in as: {self.user_name}[/bold green]")
            if self.is_page:
                console.print(f"  [cyan]📄 Mode:[/cyan] [bold white]Page[/bold white] (ID: {self.i_user})")
            else:
                console.print(f"  [cyan]👤 Mode:[/cyan] [bold white]Profile[/bold white] (ID: {self.c_user})")

            # Show token status
            dtsg = "✔" if self.tokens.get('fb_dtsg') else "✖"
            at = "✔" if self.tokens.get('access_token') else "—"
            console.print(f"  [dim]Tokens: fb_dtsg={dtsg}  access_token={at}[/dim]")
            return True

        except Exception as e:
            console.print(f"[bold red]  ✖ Error: {e}[/bold red]")
            return False

    def quick_session_check(self):
        try:
            resp = self.session.get("https://m.facebook.com/home.php",
                                     timeout=15, allow_redirects=True)
            url_l = resp.url.lower()
            if '/login' in url_l or '/checkpoint/' in url_l:
                return False
            return True
        except Exception:
            return False

    def refresh_cookies(self, new_cookie_str):
        self.raw_cookies = new_cookie_str
        self.cookies = parse_cookies(new_cookie_str)
        self.session = get_session(self.cookies)
        self.c_user = self.cookies.get('c_user')
        self.i_user = self.cookies.get('i_user')
        # Re-extract tokens
        try:
            resp = self.session.get("https://m.facebook.com/home.php", timeout=15, allow_redirects=True)
            if '/login' in resp.url.lower():
                return False
            self.tokens = extract_tokens(resp.text)
            mode = f"Page ({self.i_user})" if self.is_page else "Profile"
            console.print(f"[bold green]  ✔ Cookies refreshed — {mode}[/bold green]")
            return True
        except Exception:
            return False

    # ── Posting Methods ───────────────────────────────────────────────────

    def _try_share_scrape(self, link_url, fb_dtsg):
        """Scrape URL via ComposerLinkAttachmentPreviewQuery to get share_scrape_data."""
        try:
            variables = json.dumps({
                "feedLocation": "FEED_COMPOSER",
                "goodwillCampaignId": "",
                "goodwillCampaignMediaIds": [],
                "goodwillContentType": None,
                "params": {"url": link_url},
                "privacySelectorRenderLocation": "COMET_STREAM",
                "referringStoryRenderLocation": None,
                "renderLocation": "composer_preview",
                "parentStoryID": None,
                "scale": 1,
                "useDefaultActor": False,
                "shouldIncludeStoryAttachment": False,
                "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
                "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
                "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": False,
                "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
                "__relay_internal__pv__IsWorkUserrelayprovider": False,
                "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
                "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
                "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
                "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
                "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
                "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
            })

            post_data = {
                'av': self.target_id,
                '__user': self.target_id,
                '__a': '1',
                'dpr': '1',
                'fb_dtsg': fb_dtsg,
                'fb_api_caller_class': 'RelayModern',
                'fb_api_req_friendly_name': 'ComposerLinkAttachmentPreviewQuery',
                'variables': variables,
                'doc_id': '26033842909627970',
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://m.facebook.com',
                'Referer': 'https://m.facebook.com/',
            }

            resp = self.session.post("https://m.facebook.com/api/graphql/",
                                      data=post_data, headers=headers, timeout=30)
            text = resp.text

            # Extract share_scrape_data from response
            for p in [r'"share_scrape_data":"((?:[^"\\]|\\.)*)"',
                      r'"shareScrapeData":"((?:[^"\\]|\\.)*)"',
                      r'"share_scrape_data"\s*:\s*"((?:[^"\\]|\\.)*)"']:
                m = re.search(p, text)
                if m:
                    # Un-escape JSON string (\" → " and \\ → \)
                    try:
                        sd = json.loads('"' + m.group(1) + '"')
                    except Exception:
                        sd = m.group(1).replace('\\"', '"').replace('\\/', '/').replace('\\\\', '\\')
                    return sd
        except Exception as e:
            console.print(f"  [dim red]Scrape error: {e}[/dim red]")
        return None

    def _post_graphql(self, link_url, share_scrape_data=None):
        """Post via GraphQL ComposerStoryCreateMutation."""
        fb_dtsg = self.tokens.get('fb_dtsg')
        if not fb_dtsg:
            return None

        session_id = f"{random.randint(10000000,99999999):08x}-{random.randint(1000,9999):04x}-{random.randint(1000,9999):04x}-{random.randint(1000,9999):04x}-{random.randint(100000000000,999999999999):012x}"

        composer_input = {
            "composer_entry_point": "inline_composer",
            "composer_source_surface": "timeline",
            "idempotence_token": f"{session_id}_FEED",
            "source": "WWW",
            "audience": {"privacy": {"allow": [], "base_state": "EVERYONE", "deny": [], "tag_expansion_state": "UNSPECIFIED"}},
            "message": {"ranges": [], "text": ""},
            "with_tags_ids": None,
            "inline_activities": [],
            "text_format_preset_id": "0",
            "publishing_flow": {"supported_flows": ["ASYNC_SILENT", "ASYNC_NOTIF", "FALLBACK"]},
            "post_publish_story_data": {"reshare_post_as_sticker": "DISABLED"},
            "logging": {"composer_session_id": session_id},
            "navigation_data": {"attribution_id_v2": "ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,unexpected," + str(int(time.time() * 1000)) + ",686956,190055527696468,,"},
            "tracking": [None],
            "event_share_metadata": {"surface": "timeline"},
            "actor_id": self.target_id,
            "client_mutation_id": "1",
        }

        if share_scrape_data:
            composer_input["attachments"] = [{
                "link": {
                    "link_call_to_action_type": None,
                    "link_preview_photo_id": None,
                    "share_scrape_data": share_scrape_data
                }
            }]
        else:
            # No preview — put URL in message text
            composer_input["message"]["text"] = link_url

        variables = json.dumps({
            "input": composer_input,
            "feedLocation": "TIMELINE",
            "feedbackSource": 0,
            "focusCommentID": None,
            "gridMediaWidth": 230,
            "groupID": None,
            "scale": 1,
            "privacySelectorRenderLocation": "COMET_STREAM",
            "checkPhotosToReelsUpsellEligibility": True,
            "referringStoryRenderLocation": None,
            "renderLocation": "timeline",
            "useDefaultActor": False,
            "inviteShortLinkKey": None,
            "isFeed": False,
            "isFundraiser": False,
            "isFunFactPost": False,
            "isGroup": False,
            "isEvent": False,
            "isTimeline": True,
            "isSocialLearning": False,
            "isPageNewsFeed": False,
            "isProfileReviews": False,
            "isWorkSharedDraft": False,
            "canUserManageOffers": False,
            "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
            "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
            "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
            "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": True,
            "__relay_internal__pv__CometUFICommentAutoTranslationTyperelayprovider": "ORIGINAL",
            "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
            "__relay_internal__pv__CometUFICommentActionLinksRewriteEnabledrelayprovider": False,
            "__relay_internal__pv__IsWorkUserrelayprovider": False,
            "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
            "__relay_internal__pv__CometUFISingleLineUFIrelayprovider": True,
            "__relay_internal__pv__CometFeedStory_enable_reactor_facepilerelayprovider": False,
            "__relay_internal__pv__CometFeedStory_enable_post_permalink_white_space_clickrelayprovider": False,
            "__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider": False,
            "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
            "__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider": True,
            "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
            "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
            "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
            "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": True,
            "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": True,
            "__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider": 206,
            "__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider": False,
            "__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider": True,
            "__relay_internal__pv__groups_comet_use_glvrelayprovider": False,
            "__relay_internal__pv__GHLShouldChangeSponsoredAuctionDistanceFieldNamerelayprovider": False,
            "__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV1relayprovider": False,
            "__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV2relayprovider": False,
        })

        post_data = {
            'av': self.target_id,
            '__user': self.target_id,
            '__a': '1',
            'dpr': '1',
            'fb_dtsg': fb_dtsg,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'ComposerStoryCreateMutation',
            'variables': variables,
            'doc_id': '27616111224643858',
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://m.facebook.com',
            'Referer': 'https://m.facebook.com/',
        }

        resp = self.session.post("https://m.facebook.com/api/graphql/",
                                  data=post_data, headers=headers, timeout=30)
        text = resp.text

        if resp.status_code == 429:
            console.print(f"  [dim red]Rate limited (429)[/dim red]")
            return None
        if text.strip().startswith('<!') or text.strip().startswith('<html'):
            console.print(f"  [dim red]Got HTML instead of JSON (redirected?)[/dim red]")
            return None

        # Parse response
        for line in text.strip().split('\n'):
            line = line.strip()
            if line.startswith('for (;;);'):
                line = line[len('for (;;);'):]
            try:
                rj = json.loads(line)
                if 'errors' in rj:
                    errors = rj['errors']
                    if isinstance(errors, list) and len(errors) > 0:
                        err = errors[0]
                        err_msg = err.get('message', 'Unknown error')
                        # Check if it's a rate limit / spam block
                        if 'summary' in err and 'description' in err:
                            summary = err['summary']
                            desc = err['description'].get('__html', '')
                            # Strip HTML from description
                            desc = re.sub(r'<[^>]+>', '', desc)
                            console.print(f"  [bold red]✖ BLOCK: {summary}[/bold red]")
                            console.print(f"  [dim red]Reason: {desc}[/dim red]")
                            return 'BLOCKED'
                        else:
                            console.print(f"  [dim red]GraphQL error: {err_msg[:80]}[/dim red]")
                    return None
                if 'data' in rj and isinstance(rj['data'], dict):
                    story = rj['data'].get('story_create') or rj['data'].get('story')
                    if story is not None:
                        id_m = re.search(r'"id"\s*:\s*"(\d+)"', json.dumps(story))
                        return id_m.group(1) if id_m else "OK"
            except json.JSONDecodeError:
                continue

        if '"story_create"' in text or '"story"' in text:
            return "OK"

        # Debug: show first 200 chars of response
        console.print(f"  [dim red]Response: {text[:200]}[/dim red]")
        return None

    # ── Main Post Method ──────────────────────────────────────────────────

    def post_link(self, link_url, index=0, total=1):
        """Post a link. Returns True, False, or 'SESSION_DEAD'."""
        tag = f"[{index}/{total}]" if total > 1 else ""
        console.print(f"\n[bold cyan]{tag} Posting:[/bold cyan] [dim]{link_url}[/dim]")

        try:
            # Pre-flight check
            if not self.quick_session_check():
                console.print("[bold red]  ✖ COOKIES EXPIRED — Session dead[/bold red]")
                return 'SESSION_DEAD'

            # Refresh tokens if missing
            if not self.tokens.get('fb_dtsg'):
                resp = self.session.get(f"https://m.facebook.com/profile.php?id={self.c_user}",
                                         timeout=20, allow_redirects=True)
                self.tokens = extract_tokens(resp.text)

            fb_dtsg = self.tokens.get('fb_dtsg')

            # Step 1: Scrape URL for link preview
            console.print("  [dim]Fetching link preview...[/dim]")
            scrape_data = self._try_share_scrape(link_url, fb_dtsg)

            # Step 2: Post with preview (or text-only fallback)
            if scrape_data:
                post_id = self._post_graphql(link_url, share_scrape_data=scrape_data)
                if post_id == 'BLOCKED':
                    return False
                if post_id:
                    console.print(f"  [bold green]✔ Posted with preview![/bold green]")
                    return True

            # Fallback: post as text
            console.print("  [dim]Posting as text...[/dim]")
            post_id = self._post_graphql(link_url)
            if post_id == 'BLOCKED':
                return False
            if post_id:
                console.print(f"  [bold green]✔ Posted (text only)[/bold green]")
                return True

            console.print("  [bold red]✖ Post failed[/bold red]")
            return False

        except Exception as e:
            console.print(f"  [bold red]✖ Error: {e}[/bold red]")
            return False

    # ── Bulk Posting ──────────────────────────────────────────────────────

    def post_bulk(self, links):
        total = len(links)
        success = 0
        failed_links = []

        console.print(f"\n[bold yellow]📦 Bulk Posting: {total} links[/bold yellow]")
        console.print("[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")

        i = 0
        while i < len(links):
            link = links[i]
            result = self.post_link(link, i + 1, total)

            if result == 'SESSION_DEAD':
                console.print("\n[bold red]  🚨 COOKIES EXPIRED![/bold red]")
                nc = Prompt.ask("[bold white]  🍪 Fresh cookies (or 'q')[/bold white]")
                if nc.strip().lower() == 'q':
                    for j in range(i, len(links)):
                        failed_links.append(links[j])
                    break
                if self.refresh_cookies(nc.strip()):
                    continue
                else:
                    for j in range(i, len(links)):
                        failed_links.append(links[j])
                    break

            if result is True:
                success += 1
            else:
                failed_links.append(link)

            i += 1
            if i < len(links):
                delay = random.uniform(3, 5)
                console.print(f"  [dim]⏳ Next in {delay:.0f}s...[/dim]")
                time.sleep(delay)

        # Report
        console.print(f"\n[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")
        console.print(f"[bold white]  📊 Results: [green]{success} ✔[/green]  [red]{len(failed_links)} ✖[/red]  (Total: {total})[/bold white]")
        if failed_links:
            console.print(f"\n  [bold red]Failed links:[/bold red]")
            for idx, fl in enumerate(failed_links, 1):
                console.print(f"    [red]{idx}.[/red] [dim]{fl}[/dim]")
        console.print(f"[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")

        if failed_links:
            retry = Prompt.ask(f"\n  [yellow]⟳ Retry {len(failed_links)} failed?[/yellow]",
                               choices=["y", "n"], default="y")
            if retry == "y":
                self.post_bulk(failed_links)


# ─── Main ────────────────────────────────────────────────────────────────────

_active_bot = None

def _cleanup():
    pass  # No browser to close in requests mode

atexit.register(_cleanup)

def main():
    os.system("cls" if os.name == "nt" else "clear")
    display_banner()
    console.print("\n[dim]Bulk post links with preview using cookie auth + GraphQL.[/dim]\n")

    while True:
        console.print("[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")
        cookie_str = Prompt.ask("\n[bold white]🍪 Cookie String[/bold white]")
        if not cookie_str.strip():
            continue

        bot = FacebookPoster(cookie_str.strip())

        if not bot.validate_session():
            ans = Prompt.ask("[yellow]Retry? \\[[/yellow]y/n[yellow]\\][/yellow]", default="y").lower()
            if ans.startswith("n"):
                break
            continue

        while True:
            raw = Prompt.ask("\n[bold white]🔗 Enter link(s)[/bold white] [dim](comma-separated for bulk)[/dim]")
            if not raw.strip():
                continue

            links = [l.strip() for l in raw.split(',') if l.strip()]

            if len(links) == 1:
                console.print(f"\n[bold yellow]📋 Posting to {bot.user_name}[/bold yellow]")
                ok = bot.post_link(links[0])
                if ok == 'SESSION_DEAD':
                    console.print("\n[bold red]  🚨 COOKIES EXPIRED![/bold red]")
                    nc = Prompt.ask("[bold white]  🍪 Fresh cookies (or 'q')[/bold white]")
                    if nc.strip().lower() != 'q' and bot.refresh_cookies(nc.strip()):
                        continue
                    else:
                        break
                elif ok:
                    console.print("\n[bold green]  ✅ POST PUBLISHED![/bold green]")
                else:
                    console.print("\n[bold red]  ❌ POST FAILED[/bold red]")
            else:
                console.print(f"\n[bold yellow]📋 Posting {len(links)} links to {bot.user_name}[/bold yellow]")
                bot.post_bulk(links)

            ans1 = Prompt.ask("\n🔄 Post more? \\[y/n]", default="y").lower()
            if ans1.startswith("n"):
                break

        ans2 = Prompt.ask("🔁 Different cookies? \\[y/n]", default="n").lower()
        if ans2.startswith("n"):
            break

    console.print("\n[bold cyan]👋 Goodbye![/bold cyan]\n")


if __name__ == "__main__":
    main()
