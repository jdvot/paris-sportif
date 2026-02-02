/**
 * Weather information for match day.
 */
export interface WeatherInfo {
  available: boolean;
  temperature?: number | null;
  feels_like?: number | null;
  humidity?: number | null;
  description?: string | null;
  wind_speed?: number | null;
  rain_probability?: number | null;
  impact?: string | null;
}
