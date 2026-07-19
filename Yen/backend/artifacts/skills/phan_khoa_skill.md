# Skill: Phân khoa theo triệu chứng (Bệnh viện Tim Hà Nội)

Mục tiêu: từ mô tả triệu chứng của khách, xác định **khoa lâm sàng phù hợp nhất**, rồi suy
ra **chuyên khoa để đưa vào event "result"** (hiện chỉ có đúng 1 trong 4 giá trị hợp lệ cho
`xem_lich_kham` sau này: `"Tim mạch"`, `"Nhi"`, `"Da liễu"`, `"Nội tổng quát"`).

Nguồn dữ liệu chi tiết: `data/structured/trieu_chung_phan_khoa.csv` (24 khoa, đầy đủ câu
hỏi sàng lọc + mức khẩn cấp). File này là bản tóm tắt để dùng trực tiếp trong hội thoại.

## 0. Luật khẩn cấp — luôn kiểm tra trước tiên

Nếu có bất kỳ dấu hiệu sau: đau ngực dữ dội, khó thở đột ngột, ngất/ngừng tim, vã mồ hôi
lạnh, đau lan vai trái/hàm, tim đập rất nhanh/loạn nhịp kèm choáng, nói khó/liệt nửa người
→ **BỎ QUA mọi bước phân khoa bên dưới**, phát sự kiện `emergency`, hướng dẫn gọi **115**
hoặc đến **Khoa Cấp cứu** ngay. Không hỏi thêm câu sàng lọc nào nữa.

## 1. Quy trình phân khoa

1. Thu thập triệu chứng chính (tối đa 1 câu hỏi/lượt, theo quy tắc chung của hệ thống).
2. Đối chiếu triệu chứng với bảng ở mục 2 để chọn **khoa lâm sàng** khớp nhất.
3. Nếu khoa đó thuộc nhóm **"Chuyển tuyến nội viện"** (phẫu thuật, hồi sức, gây mê) — đây
   KHÔNG phải điểm đặt lịch trực tiếp cho khách mới. Nói rõ với khách rằng đây là bước sau
   khi bác sĩ Nội/Can thiệp đã chẩn đoán và chỉ định, rồi hạ về khoa "tiếp nhận trực tiếp"
   gần nhất (ví dụ nghi cần phẫu thuật tim → vẫn hướng khách đặt lịch khoa Nội hoặc Tim
   mạch can thiệp trước để được chẩn đoán và chuyển tuyến đúng quy trình).
4. Dùng bảng ánh xạ ở mục 3 để chuyển khoa chi tiết → 1 trong 4 chuyên khoa demo, đưa vào
   event "result" (xem mục FINAL ASSESSMENT của system prompt chính).
5. KHÔNG gọi `xem_lich_kham` ngay ở bước này — theo quy tắc chung, phải hỏi khách có muốn
   tìm bác sĩ/đặt lịch không trước (event "question" ngay sau "result"). Nếu khách đồng ý,
   hỏi tiếp ngày/khung giờ muốn khám nếu khách chưa nói. Chỉ gọi
   `xem_lich_kham(query=<chuyên khoa đã ánh xạ>, preferred_date=..., preferred_time_period=..., preferred_time_slot=...)`
   SAU KHI đã có mong muốn thời gian, hoặc `flexible_time=true` nếu khách nói ngày/giờ nào cũng được.

## 2. Bảng phân khoa theo triệu chứng

| Khoa | Loại tiếp nhận | Dấu hiệu/triệu chứng chính | Mức khẩn cấp |
|---|---|---|---|
| Khoa Cấp cứu | Trực tiếp | Đau ngực dữ dội, khó thở đột ngột, ngất, ngừng tim, nhồi máu cơ tim | Khẩn cấp |
| Khoa Khám bệnh | Trực tiếp | Triệu chứng tim mạch chưa rõ nguyên nhân, khám sàng lọc, có BHYT | Thường quy |
| Khoa Khám bệnh tự nguyện | Trực tiếp | Muốn khám dịch vụ/tự nguyện, tầm soát tim mạch tổng quát | Thường quy |
| Khoa Quốc tế | Trực tiếp | Bệnh nhân nước ngoài, cần phiên dịch/bảo hiểm quốc tế, dịch vụ cao cấp | Thường quy |
| Khoa Nội | Trực tiếp | Suy tim, tăng huyết áp, rối loạn lipid máu, bệnh mạn tính cần chỉnh thuốc dài hạn | Thường quy |
| Khoa Điều trị ban ngày | Trực tiếp | Cần truyền thuốc/thủ thuật ngắn, không cần nằm viện qua đêm | Thường quy |
| Khoa Tim mạch chuyển hóa | Trực tiếp | Đái tháo đường, béo phì, rối loạn lipid ảnh hưởng tim | Thường quy |
| Khoa các bệnh mạch máu | Trực tiếp | Suy giãn tĩnh mạch, tắc hẹp động mạch chi, sưng/đau/tê chân | Thường quy |
| Khoa Dinh dưỡng | Trực tiếp | Cần tư vấn chế độ ăn tim mạch, dinh dưỡng sau mổ/hồi sức | Thường quy |
| Phòng khám đa khoa | Trực tiếp | Triệu chứng không thuộc tim mạch, cần khám chuyên khoa khác kèm theo | Thường quy |
| Khoa Tim mạch can thiệp | Trực tiếp | Đã/nghi hẹp-tắc mạch vành, cần đặt stent/nong mạch | Khẩn cấp hoặc theo hẹn |
| Khoa Can thiệp tĩnh mạch | Trực tiếp | Suy giãn tĩnh mạch/huyết khối tĩnh mạch sâu cần can thiệp | Thường quy |
| Khoa Thăm dò điện sinh lý & rối loạn nhịp | Trực tiếp | Hồi hộp, tim đập nhanh/chậm bất thường, ngất không rõ nguyên nhân | Thường quy |
| Khoa Nội nhi | Trực tiếp | Trẻ mệt, khó thở, tím tái, chậm lớn nghi tim mạch | Thường quy |
| Khoa Can thiệp tim mạch trẻ em | Trực tiếp | Dị tật tim bẩm sinh cần đóng lỗ thông/nong van qua da | Theo hẹn |
| Khoa Phẫu thuật tim người lớn | Chuyển tuyến | Đã chỉ định mổ tim hở: thay van, bắc cầu mạch vành | Theo lịch mổ |
| Khoa Phẫu thuật mạch máu | Chuyển tuyến | Phình động mạch chủ, tắc mạch máu ngoại biên cần mổ | Theo lịch mổ |
| Đơn vị phẫu thuật tim ít xâm lấn | Chuyển tuyến | Cần mổ tim qua đường mổ nhỏ/nội soi | Theo lịch mổ |
| Khoa Hồi sức tích cực | Chuyển tuyến | Bệnh nhân nặng sau mổ tim/bệnh tim nguy kịch | Khẩn cấp (nội viện) |
| Khoa Phẫu thuật tim trẻ em | Chuyển tuyến | Dị tật tim bẩm sinh ở trẻ sơ sinh/nhỏ cần mổ | Theo lịch mổ |
| Khoa Hồi sức tích cực nhi | Chuyển tuyến | Hồi sức trẻ em sau mổ tim/bệnh tim nặng | Khẩn cấp (nội viện) |

*(Bảng đầy đủ 24 khoa + câu hỏi sàng lọc chi tiết: xem `trieu_chung_phan_khoa.csv`.)*

## 3. Ánh xạ về 4 chuyên khoa cho `xem_lich_kham`

Dữ liệu đặt lịch demo hiện chỉ có 4 chuyên khoa — mọi khoa tim mạch (người lớn) ở mục 2
đều gọi là `"Tim mạch"` khi đặt lịch:

| Nhóm khoa (mục 2) | Chuyên khoa gọi `xem_lich_kham` |
|---|---|
| Mọi khoa tim mạch người lớn (Khám bệnh, Khám bệnh tự nguyện, Quốc tế, Nội, Điều trị ban ngày, Tim mạch chuyển hóa, các bệnh mạch máu, Dinh dưỡng, Tim mạch can thiệp, Can thiệp tĩnh mạch, Thăm dò điện sinh lý, Phẫu thuật tim/mạch máu người lớn, Hồi sức tích cực) | `"Tim mạch"` |
| Mọi khoa thuộc Trung tâm Tim mạch Nhi (Nội nhi, Can thiệp tim mạch trẻ em, Phẫu thuật tim trẻ em, Hồi sức tích cực nhi) | `"Nhi"` |
| Phòng khám đa khoa — triệu chứng ngoài da | `"Da liễu"` |
| Phòng khám đa khoa — triệu chứng khác không rõ chuyên khoa | `"Nội tổng quát"` |
| Khoa Cấp cứu | *(không đặt lịch — hướng dẫn gọi 115/đến cấp cứu ngay, không gọi `xem_lich_kham`)* |

Lưu ý: bệnh viện thực tế không có khoa Da liễu riêng (đây là chuyên khoa chỉ tồn tại
trong dữ liệu demo đặt lịch) — chỉ dùng `"Da liễu"` khi khách hỏi đúng vấn đề về da và
không có lựa chọn nào khác phù hợp hơn.
