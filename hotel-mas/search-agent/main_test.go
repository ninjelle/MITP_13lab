package main

import (
	"testing"
	"time"
)

func TestValidateRequest_ValidInput(t *testing.T) {
	req := SearchRequest{
		TaskID:   "task-001",
		City:     "moscow",
		CheckIn:  "2025-09-01",
		CheckOut: "2025-09-05",
		Guests:   2,
	}
	if err := validateRequest(req); err != nil {
		t.Errorf("Ожидался nil, получено: %v", err)
	}
}

func TestValidateRequest_MissingCity(t *testing.T) {
	req := SearchRequest{
		TaskID:   "task-002",
		CheckIn:  "2025-09-01",
		CheckOut: "2025-09-05",
		Guests:   1,
	}
	if err := validateRequest(req); err == nil {
		t.Error("Ожидалась ошибка при пустом city")
	}
}

func TestValidateRequest_CheckOutBeforeCheckIn(t *testing.T) {
	req := SearchRequest{
		TaskID:   "task-003",
		City:     "moscow",
		CheckIn:  "2025-09-10",
		CheckOut: "2025-09-05", // раньше check_in
		Guests:   1,
	}
	if err := validateRequest(req); err == nil {
		t.Error("Ожидалась ошибка: check_out раньше check_in")
	}
}

func TestValidateRequest_ZeroGuests(t *testing.T) {
	req := SearchRequest{
		TaskID:   "task-004",
		City:     "moscow",
		CheckIn:  "2025-09-01",
		CheckOut: "2025-09-05",
		Guests:   0,
	}
	if err := validateRequest(req); err == nil {
		t.Error("Ожидалась ошибка при guests=0")
	}
}

func TestValidateRequest_InvalidDateFormat(t *testing.T) {
	req := SearchRequest{
		TaskID:   "task-005",
		City:     "moscow",
		CheckIn:  "01-09-2025", // неверный формат
		CheckOut: "2025-09-05",
		Guests:   1,
	}
	if err := validateRequest(req); err == nil {
		t.Error("Ожидалась ошибка при неверном формате даты")
	}
}


func TestIsRoomAvailable_NoBookings(t *testing.T) {
	room := Room{
		RoomID:   "test-room",
		Bookings: []Booking{},
	}
	checkIn := mustParse("2025-09-01")
	checkOut := mustParse("2025-09-05")

	if !isRoomAvailable(room, checkIn, checkOut) {
		t.Error("Номер без броней должен быть доступен")
	}
}

func TestIsRoomAvailable_ExactOverlap(t *testing.T) {
	room := Room{
		RoomID: "test-room",
		Bookings: []Booking{
			{mustParse("2025-09-01"), mustParse("2025-09-05")},
		},
	}
	// Те же даты — должен быть занят
	if isRoomAvailable(room, mustParse("2025-09-01"), mustParse("2025-09-05")) {
		t.Error("Номер с совпадающей бронью должен быть недоступен")
	}
}

func TestIsRoomAvailable_PartialOverlap(t *testing.T) {
	room := Room{
		RoomID: "test-room",
		Bookings: []Booking{
			{mustParse("2025-09-03"), mustParse("2025-09-08")},
		},
	}
	// Запрос 01–06 пересекается с 03–08
	if isRoomAvailable(room, mustParse("2025-09-01"), mustParse("2025-09-06")) {
		t.Error("Номер с частичным пересечением должен быть недоступен")
	}
}

func TestIsRoomAvailable_AdjacentBooking(t *testing.T) {
	room := Room{
		RoomID: "test-room",
		Bookings: []Booking{
			{mustParse("2025-09-05"), mustParse("2025-09-10")},
		},
	}
	// Запрос 01–05: check_out совпадает с началом брони — не пересекается
	if !isRoomAvailable(room, mustParse("2025-09-01"), mustParse("2025-09-05")) {
		t.Error("Смежные (не перекрывающиеся) периоды должны считаться доступными")
	}
}


func TestSearchRooms_CityFilter(t *testing.T) {
	req := SearchRequest{
		TaskID:   "task-010",
		City:     "sochi",
		CheckIn:  "2025-09-01",
		CheckOut: "2025-09-05",
		Guests:   2,
	}
	rooms, err := searchRooms(req)
	if err != nil {
		t.Fatalf("Неожиданная ошибка: %v", err)
	}
	for _, r := range rooms {
		if r.HotelName != "Seaside Resort" {
			t.Errorf("Ожидался отель в Сочи, получен: %s", r.HotelName)
		}
	}
}

func TestSearchRooms_CapacityFilter(t *testing.T) {
	req := SearchRequest{
		TaskID:   "task-011",
		City:     "moscow",
		CheckIn:  "2025-09-01",
		CheckOut: "2025-09-05",
		Guests:   4, // только suite вмещает 4
	}
	rooms, err := searchRooms(req)
	if err != nil {
		t.Fatalf("Неожиданная ошибка: %v", err)
	}
	for _, r := range rooms {
		if r.RoomType != "suite" {
			t.Errorf("При guests=4 должны приходить только suite, получен: %s", r.RoomType)
		}
	}
}

func TestSearchRooms_MaxPriceFilter(t *testing.T) {
	req := SearchRequest{
		TaskID:   "task-012",
		City:     "moscow",
		CheckIn:  "2025-09-01",
		CheckOut: "2025-09-05",
		Guests:   1,
		MaxPrice: 3000, // только room-301 (2800₽) попадает
	}
	rooms, err := searchRooms(req)
	if err != nil {
		t.Fatalf("Неожиданная ошибка: %v", err)
	}
	for _, r := range rooms {
		if r.PricePerNight > 3000 {
			t.Errorf("Цена %v превышает MaxPrice 3000", r.PricePerNight)
		}
	}
}

func TestSearchRooms_TotalPriceCalculation(t *testing.T) {
	req := SearchRequest{
		TaskID:   "task-013",
		City:     "sochi",
		CheckIn:  "2025-09-01",
		CheckOut: "2025-09-04", // 3 ночи
		Guests:   2,
		RoomType: "double",
	}
	rooms, err := searchRooms(req)
	if err != nil {
		t.Fatalf("Неожиданная ошибка: %v", err)
	}
	if len(rooms) == 0 {
		t.Fatal("Ожидался хотя бы один номер")
	}
	expected := rooms[0].PricePerNight * 3
	if rooms[0].TotalPrice != expected {
		t.Errorf("TotalPrice: ожидалось %.2f, получено %.2f", expected, rooms[0].TotalPrice)
	}
}

func TestSearchRooms_UnavailableRoom(t *testing.T) {
	// room-101 занят 10–15 июля 2025
	req := SearchRequest{
		TaskID:   "task-014",
		City:     "moscow",
		CheckIn:  "2025-07-12",
		CheckOut: "2025-07-14",
		Guests:   1,
		RoomType: "single",
	}
	rooms, err := searchRooms(req)
	if err != nil {
		t.Fatalf("Неожиданная ошибка: %v", err)
	}
	for _, r := range rooms {
		if r.RoomID == "room-101" {
			t.Error("room-101 занят в этот период и не должен появляться в результатах")
		}
	}
}

// Вспомогательная функция для тестов (дублируем, т.к. тесты в том же пакете)
var _ = time.Now // чтобы пакет time не был "unused" в тестах
