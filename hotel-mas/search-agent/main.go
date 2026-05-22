package main

import "time"

const (
    TopicSearchRequest = "hotel.search.request"
    TopicSearchResult  = "hotel.search.result"
    TopicSearchError   = "hotel.search.error"
)

type SearchRequest struct {
    TaskID   string  `json:"task_id"`
    City     string  `json:"city"`
    CheckIn  string  `json:"check_in"`
    CheckOut string  `json:"check_out"`
    Guests   int     `json:"guests"`
    RoomType string  `json:"room_type,omitempty"`
    MaxPrice float64 `json:"max_price,omitempty"`
}

type RoomOffer struct {
    RoomID        string  `json:"room_id"`
    HotelName     string  `json:"hotel_name"`
    RoomType      string  `json:"room_type"`
    Capacity      int     `json:"capacity"`
    PricePerNight float64 `json:"price_per_night"`
    TotalPrice    float64 `json:"total_price"`
    Available     bool    `json:"available"`
}

type SearchResult struct {
    TaskID     string      `json:"task_id"`
    Success    bool        `json:"success"`
    Rooms      []RoomOffer `json:"rooms"`
    Count      int         `json:"count"`
    SearchedAt string      `json:"searched_at"`
}

type ErrorResult struct {
    TaskID  string `json:"task_id"`
    Success bool   `json:"success"`
    Error   string `json:"error"`
}

type Room struct {
    RoomID        string
    HotelName     string
    City          string
    RoomType      string
    Capacity      int
    PricePerNight float64
    Bookings      []Booking
}

type Booking struct {
    CheckIn  time.Time
    CheckOut time.Time
}

func mustParse(s string) time.Time {
    t, _ := time.Parse("2006-01-02", s)
    return t
}

var roomDatabase = []Room{
    {
        RoomID: "room-101", HotelName: "Grand Hotel", City: "moscow",
        RoomType: "single", Capacity: 1, PricePerNight: 3500.0,
        Bookings: []Booking{{mustParse("2025-07-10"), mustParse("2025-07-15")}},
    },
    {
        RoomID: "room-102", HotelName: "Grand Hotel", City: "moscow",
        RoomType: "double", Capacity: 2, PricePerNight: 5500.0,
        Bookings: []Booking{},
    },
    {
        RoomID: "room-201", HotelName: "Grand Hotel", City: "moscow",
        RoomType: "suite", Capacity: 4, PricePerNight: 12000.0,
        Bookings: []Booking{{mustParse("2025-08-01"), mustParse("2025-08-05")}},
    },
    {
        RoomID: "room-301", HotelName: "City Inn", City: "moscow",
        RoomType: "single", Capacity: 1, PricePerNight: 2800.0,
        Bookings: []Booking{},
    },
    {
        RoomID: "room-401", HotelName: "Seaside Resort", City: "sochi",
        RoomType: "double", Capacity: 2, PricePerNight: 6800.0,
        Bookings: []Booking{},
    },
    {
        RoomID: "room-402", HotelName: "Seaside Resort", City: "sochi",
        RoomType: "suite", Capacity: 4, PricePerNight: 15000.0,
        Bookings: []Booking{},
    },
}

func validateRequest(req SearchRequest) error {
    if req.City == "" {
        return fmt.Errorf("поле city обязательно")
    }
    checkIn, err := time.Parse("2006-01-02", req.CheckIn)
    if err != nil {
        return fmt.Errorf("неверный формат check_in")
    }
    checkOut, err := time.Parse("2006-01-02", req.CheckOut)
    if err != nil {
        return fmt.Errorf("неверный формат check_out")
    }
    if !checkOut.After(checkIn) {
        return fmt.Errorf("check_out должен быть позже check_in")
    }
    if req.Guests < 1 {
        return fmt.Errorf("количество гостей должно быть не менее 1")
    }
    if checkIn.After(time.Now().AddDate(1, 0, 0)) {
        return fmt.Errorf("дата заезда не может быть позже чем через 365 дней")
    }
    return nil
}

func isRoomAvailable(room Room, checkIn, checkOut time.Time) bool {
    for _, b := range room.Bookings {
        if checkIn.Before(b.CheckOut) && checkOut.After(b.CheckIn) {
            return false
        }
    }
    return true
}

func searchRooms(req SearchRequest) ([]RoomOffer, error) {
    checkIn, _ := time.Parse("2006-01-02", req.CheckIn)
    checkOut, _ := time.Parse("2006-01-02", req.CheckOut)
    nights := int(checkOut.Sub(checkIn).Hours() / 24)

    var results []RoomOffer
    for _, room := range roomDatabase {
        if !strings.EqualFold(room.City, req.City) {
            continue
        }
        if room.Capacity < req.Guests {
            continue
        }
        if req.RoomType != "" && !strings.EqualFold(room.RoomType, req.RoomType) {
            continue
        }
        if req.MaxPrice > 0 && room.PricePerNight > req.MaxPrice {
            continue
        }
        if !isRoomAvailable(room, checkIn, checkOut) {
            continue
        }
        results = append(results, RoomOffer{
            RoomID:        room.RoomID,
            HotelName:     room.HotelName,
            RoomType:      room.RoomType,
            Capacity:      room.Capacity,
            PricePerNight: room.PricePerNight,
            TotalPrice:    room.PricePerNight * float64(nights),
            Available:     true,
        })
    }
    return results, nil
}