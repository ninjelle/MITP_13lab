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