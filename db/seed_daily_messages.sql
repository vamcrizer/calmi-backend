-- Seed data for Daily Kind Messages
-- Run this SQL to populate the daily_kind_messages table

-- Clear existing data (optional)
-- DELETE FROM daily_kind_messages;

-- Insert messages for the next 30 days
INSERT INTO daily_kind_messages (message_text, active_date, created_at) VALUES
('Hôm nay, hãy thử nói một lời tốt đẹp với bạn bè hoặc người thân nhé! 💚', CURRENT_DATE, NOW()),
('Một nụ cười nhỏ có thể làm sáng cả ngày của ai đó. Hãy mỉm cười thật nhiều hôm nay! 😊', CURRENT_DATE + INTERVAL '1 day', NOW()),
('Giúp đỡ ai đó hôm nay, dù là việc nhỏ. Bạn sẽ thấy vui lắm đấy! 🌟', CURRENT_DATE + INTERVAL '2 day', NOW()),
('Hãy lắng nghe khi bạn bè chia sẻ. Đôi khi chỉ cần được lắng nghe là đủ. 💙', CURRENT_DATE + INTERVAL '3 day', NOW()),
('Cảm ơn ai đó đã giúp đỡ bạn. Lòng biết ơn làm cuộc sống tốt đẹp hơn! 🙏', CURRENT_DATE + INTERVAL '4 day', NOW()),
('Chia sẻ đồ ăn, đồ chơi với bạn. Niềm vui được nhân đôi khi chia sẻ! 🤝', CURRENT_DATE + INTERVAL '5 day', NOW()),
('Hãy kiên nhẫn với bản thân. Ai cũng có lúc sai, quan trọng là biết sửa. 💪', CURRENT_DATE + INTERVAL '6 day', NOW()),
('Ôm bố mẹ hoặc người thân một cái. Tình yêu thương không cần nhiều lời! 🤗', CURRENT_DATE + INTERVAL '7 day', NOW()),
('Hãy dọn dẹp góc học tập của mình. Không gian gọn gàng, tâm trí thư thái! ✨', CURRENT_DATE + INTERVAL '8 day', NOW()),
('Chơi cùng em nhỏ hoặc giúp đỡ các em. Bạn là tấm gương tốt đấy! 🌈', CURRENT_DATE + INTERVAL '9 day', NOW()),
('Hãy tha thứ cho ai đó đã làm bạn buồn. Tha thứ giúp lòng nhẹ nhõm hơn. 🕊️', CURRENT_DATE + INTERVAL '10 day', NOW()),
('Viết một lời chúc tốt đẹp gửi đến bạn bè. Những lời yêu thương luôn lan tỏa! 💌', CURRENT_DATE + INTERVAL '11 day', NOW()),
('Hãy ra ngoài hít thở không khí trong lành. Thiên nhiên mang đến sự bình yên. 🌳', CURRENT_DATE + INTERVAL '12 day', NOW()),
('Kể cho bố mẹ nghe một ngày của con. Họ luôn muốn biết bạn đang làm gì! 👨‍👩‍👧', CURRENT_DATE + INTERVAL '13 day', NOW()),
('Hãy thử một việc mới hôm nay. Mọi thay đổi đều bắt đầu từ bước đầu tiên! 🚀', CURRENT_DATE + INTERVAL '14 day', NOW()),
('Đọc một cuốn sách hoặc truyện. Sách mở ra cả thế giới mới! 📚', CURRENT_DATE + INTERVAL '15 day', NOW()),
('Hãy tự khen ngợi bản thân vì những điều tốt bạn đã làm. Bạn thật tuyệt! ⭐', CURRENT_DATE + INTERVAL '16 day', NOW()),
('Giúp thầy cô hoặc bạn bè dọn dẹp lớp học. Cùng nhau làm mọi thứ dễ hơn! 🧹', CURRENT_DATE + INTERVAL '17 day', NOW()),
('Hãy ngủ sớm tối nay. Giấc ngủ ngon giúp bạn khỏe mạnh và vui vẻ! 😴', CURRENT_DATE + INTERVAL '18 day', NOW()),
('Vẽ hoặc viết gì đó cho người bạn yêu thương. Quà handmade ý nghĩa lắm! 🎨', CURRENT_DATE + INTERVAL '19 day', NOW()),
('Hãy mỉm cười với một người lạ. Sự thân thiện làm thế giới tốt đẹp hơn! 🌸', CURRENT_DATE + INTERVAL '20 day', NOW()),
('Tập thể dục hoặc chơi thể thao. Vận động giúp cơ thể và tinh thần khỏe! 🏃', CURRENT_DATE + INTERVAL '21 day', NOW()),
('Hãy nói "Mình xin lỗi" nếu bạn đã sai. Xin lỗi cần sự dũng cảm! 💜', CURRENT_DATE + INTERVAL '22 day', NOW()),
('Gọi điện hoặc nhắn tin hỏi thăm ông bà. Họ nhớ bạn nhiều lắm! 📞', CURRENT_DATE + INTERVAL '23 day', NOW()),
('Hãy uống đủ nước và ăn một bữa ăn ngon. Chăm sóc bản thân là yêu thương mình! 🍎', CURRENT_DATE + INTERVAL '24 day', NOW()),
('Chơi với thú cưng hoặc chăm sóc cây cối. Yêu thương lan tỏa đến mọi sinh vật! 🐾', CURRENT_DATE + INTERVAL '25 day', NOW()),
('Hãy viết nhật ký về những điều tốt đẹp trong ngày. Biết ơn mang đến hạnh phúc! 📝', CURRENT_DATE + INTERVAL '26 day', NOW()),
('Chia sẻ với bạn bè về sở thích của mình. Kết nối làm tình bạn bền chặt! 💛', CURRENT_DATE + INTERVAL '27 day', NOW()),
('Hãy tắt điện thoại và dành thời gian cho gia đình. Những khoảnh khắc bên nhau rất quý! 👨‍👩‍👧‍👦', CURRENT_DATE + INTERVAL '28 day', NOW()),
('Hít sâu, thở chậm. Mỗi ngày là một cơ hội mới để lan tỏa năng lượng tích cực! 🌞', CURRENT_DATE + INTERVAL '29 day', NOW())
ON CONFLICT (active_date) DO UPDATE SET message_text = EXCLUDED.message_text;

-- Verify inserted data
SELECT COUNT(*) as total_messages FROM daily_kind_messages;
