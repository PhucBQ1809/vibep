# digestbot — Bản tin tổng hợp hằng ngày gửi Telegram

Mỗi sáng bot đọc RSS từ nhiều nguồn (Google News, blog, Reddit...), lọc theo từ khoá, bỏ bài trùng/cũ,
chấm điểm rồi gửi **top bài hay nhất** vào chat Telegram của bạn.

Hiện có sẵn chủ đề **MMO (kiếm tiền online)**, và mẫu chủ đề **IT** (đang tắt). Thêm chủ đề mới chỉ cần sửa
file `config/topics.yaml`, không phải sửa code.

```
RSS nguồn ──► fetch (song song) ──► lọc: tuổi bài, từ khoá, đã gửi chưa, trùng lặp
                                     └► chấm điểm (độ ưu tiên nguồn × từ khoá boost × độ mới)
                                          └► top N bài ──► Telegram (HTML, tự chia tin nhắn dài)
                                                             └► lưu data/sent.json (không gửi lại)
```

## 1. Tạo bot Telegram

1. Chat với [@BotFather](https://t.me/BotFather) → `/newbot` → lấy **token**.
2. Lấy **chat id**:
   - Chat riêng: nhắn bất kỳ cho bot của bạn, rồi mở
     `https://api.telegram.org/bot<TOKEN>/getUpdates` → tìm `"chat":{"id": ...}`.
   - Group: thêm bot vào group, nhắn 1 tin trong group, mở link trên (id group dạng `-100...`).
   - Kênh: thêm bot làm admin kênh, chat id là `@ten_kenh` hoặc `-100...`.

## 2. Chạy tự động hằng ngày bằng GitHub Actions (miễn phí)

1. Vào repo trên GitHub → **Settings → Secrets and variables → Actions → New repository secret**, tạo:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. **Settings → Actions → General → Workflow permissions**: chọn *Read and write permissions*
   (để bot commit lại `data/sent.json`, tránh gửi trùng bài).
3. Workflow `.github/workflows/daily-digest.yml` chạy lúc **08:00 giờ VN** mỗi ngày.
   Muốn chạy thử ngay: tab **Actions → Daily digest → Run workflow** (có tuỳ chọn `dry_run`).

Đổi giờ gửi: sửa dòng `cron` (giờ UTC = giờ VN − 7).

> Lưu ý: workflow lịch hẹn của GitHub chỉ chạy trên nhánh mặc định (thường là `main`),
> và sẽ tự tắt nếu repo không có hoạt động trong 60 ngày.

## 3. Chạy trên máy

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m digestbot --list                  # xem các topic
python -m digestbot --topic mmo --dry-run   # in bản tin ra màn hình, không gửi

export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
python -m digestbot                         # gửi tất cả topic đang bật
```

## 4. Thêm / chỉnh chủ đề

Mở `config/topics.yaml`:

- **Bật chủ đề IT**: đổi `enabled: false` → `true`.
- **Gửi topic sang group khác**: đặt `chat_id_env: "TELEGRAM_CHAT_ID_IT"`, tạo secret cùng tên và
  bỏ comment dòng tương ứng trong `daily-digest.yml`.
- **Thêm nguồn**: thêm `- name: ... url: ...` vào `sources`. Nguồn nào quan trọng thì tăng `weight`.
  - Google News theo từ khoá: `https://news.google.com/rss/search?q=<từ+khoá>+when:1d&hl=vi&gl=VN&ceid=VN:vi`
  - Reddit: `https://www.reddit.com/r/<sub>/top/.rss?t=day`
  - Hầu hết blog WordPress: `https://<domain>/feed/`
- **Lọc nội dung**: `exclude_keywords` (loại bỏ), `include_keywords` (bắt buộc có),
  `boost_keywords` (ưu tiên). So khớp theo nguyên từ, không phân biệt hoa thường, hỗ trợ tiếng Việt có dấu.
- **Thêm chủ đề mới**: copy nguyên block `it:` thành id mới (vd `crypto:`), đổi title/sources.

Một nguồn lỗi (timeout, bị chặn) chỉ bị bỏ qua và ghi log, không làm hỏng cả bản tin.
Reddit đôi khi chặn IP của GitHub Actions — khi đó các nguồn khác vẫn chạy bình thường.

## Cấu trúc code

| File | Vai trò |
|---|---|
| `digestbot/config.py` | Đọc `topics.yaml` |
| `digestbot/sources.py` | Lấy bài từ nguồn. Thêm loại nguồn mới (API, scrape...) bằng cách đăng ký hàm vào `FETCHERS` |
| `digestbot/ranking.py` | Lọc, bỏ trùng, chấm điểm, chọn top bài |
| `digestbot/formatter.py` | Định dạng tin nhắn Telegram |
| `digestbot/telegram.py` | Gửi tin (có retry, xử lý rate limit) |
| `digestbot/state.py` | Lưu các bài đã gửi (giữ 30 ngày) |
| `digestbot/pipeline.py` | Ghép các bước cho 1 topic |

Chạy test: `pip install pytest && pytest -q`

## Hướng phát triển

- Tóm tắt bài bằng AI (Claude API) trước khi gửi, hoặc để AI chấm điểm độ "hay" của bài.
- Nút bấm 👍/👎 trên Telegram để học sở thích và điều chỉnh `weight` nguồn.
- Thêm loại nguồn: YouTube channel (có RSS sẵn), Twitter/X, Facebook group, Viblo...
