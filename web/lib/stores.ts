export type Stockist = {
  name: string;
  type: "Flagship" | "Stockist" | "Showroom";
  city: string;
  country: string;
  address: string[];
  hours: string[];
  phone?: string;
  mapUrl: string;
};

export const stockists: Stockist[] = [
  {
    name: "BASIC Amsterdam",
    type: "Flagship",
    city: "Amsterdam",
    country: "Netherlands",
    address: ["Keizersgracht 241", "1016 EA Amsterdam"],
    hours: ["Mon – Sat, 10:00 – 18:00", "Sun, 12:00 – 17:00"],
    phone: "+31 20 123 4567",
    mapUrl: "https://www.openstreetmap.org/search?query=Keizersgracht%20241%20Amsterdam",
  },
  {
    name: "BASIC Studio & Showroom",
    type: "Showroom",
    city: "Amsterdam",
    country: "Netherlands",
    address: ["Distelweg 88", "1031 HH Amsterdam"],
    hours: ["By appointment, Mon – Fri"],
    mapUrl: "https://www.openstreetmap.org/search?query=Distelweg%2088%20Amsterdam",
  },
  {
    name: "Atelier Nord",
    type: "Stockist",
    city: "Copenhagen",
    country: "Denmark",
    address: ["Elmegade 12", "2200 København N"],
    hours: ["Mon – Sat, 11:00 – 18:00"],
    mapUrl: "https://www.openstreetmap.org/search?query=Elmegade%2012%20Copenhagen",
  },
  {
    name: "Maison Neuf",
    type: "Stockist",
    city: "Paris",
    country: "France",
    address: ["9 Rue de Poitou", "75003 Paris"],
    hours: ["Tue – Sat, 11:00 – 19:00"],
    mapUrl: "https://www.openstreetmap.org/search?query=9%20Rue%20de%20Poitou%20Paris",
  },
  {
    name: "Goods & Supply",
    type: "Stockist",
    city: "Berlin",
    country: "Germany",
    address: ["Torstraße 140", "10119 Berlin"],
    hours: ["Mon – Sat, 12:00 – 19:00"],
    mapUrl: "https://www.openstreetmap.org/search?query=Torstrasse%20140%20Berlin",
  },
  {
    name: "The Reading Room",
    type: "Stockist",
    city: "London",
    country: "United Kingdom",
    address: ["46 Redchurch Street", "London E2 7DP"],
    hours: ["Mon – Sat, 10:00 – 18:00", "Sun, 11:00 – 17:00"],
    mapUrl: "https://www.openstreetmap.org/search?query=46%20Redchurch%20Street%20London",
  },
  {
    name: "Kura",
    type: "Stockist",
    city: "Tokyo",
    country: "Japan",
    address: ["2-11-5 Jingumae", "Shibuya City, Tokyo 150-0001"],
    hours: ["Daily, 11:00 – 20:00"],
    mapUrl: "https://www.openstreetmap.org/search?query=2-11-5%20Jingumae%20Tokyo",
  },
  {
    name: "Field Supply Co.",
    type: "Stockist",
    city: "New York",
    country: "United States",
    address: ["148 Orchard Street", "New York, NY 10002"],
    hours: ["Mon – Sun, 11:00 – 19:00"],
    mapUrl: "https://www.openstreetmap.org/search?query=148%20Orchard%20Street%20New%20York",
  },
];

export function stockistsByCountry() {
  const grouped = new Map<string, Stockist[]>();
  for (const s of stockists) {
    grouped.set(s.country, [...(grouped.get(s.country) ?? []), s]);
  }
  return [...grouped.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}
