/**
 * Mock data for development and testing
 * This file provides realistic sample data for the sports betting application
 */

import type {
  Match,
  DetailedPrediction,
  TeamForm,
} from "./types";

/**
 * Mock match data
 */
export const mockMatch: Match = {
  id: 1,
  homeTeam: "Manchester United",
  awayTeam: "Liverpool",
  competition: "Premier League",
  competitionCode: "PL",
  matchDate: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // Tomorrow
  status: "scheduled",
  matchday: 20,
};

/**
 * Mock detailed prediction
 */
export const mockPrediction: DetailedPrediction = {
  homeProb: 0.48,
  drawProb: 0.28,
  awayProb: 0.24,
  recommendedBet: "home",
  confidence: 0.72,
  valueScore: 0.15,
  explanation:
    "Manchester United shows strong home form with 4 wins in last 5 games at Old Trafford. Liverpool's away record is weakening with only 1 win in recent 5 away matches. Tactical advantage favors home team with better midfield control.",
  keyFactors: [
    "Manchester United undefeated at home in last 6 matches",
    "Liverpool struggling away from Anfield with 1W-2D-2L in last 5",
    "Historical H2H slightly favors United with 12W-8D-10L record",
    "Expected goals model favors home team (2.3 vs 1.8)",
    "Recent form: United 4W-1D, Liverpool 3W-1D-1L",
  ],
  riskFactors: [
    "Potential injuries affecting key United players",
    "High stakes match could lead to cautious play",
    "Liverpool has beaten strong teams this season",
  ],
  modelContributions: {
    poisson: {
      homeProb: 0.50,
      drawProb: 0.30,
      awayProb: 0.20,
      weight: 0.25,
    },
    elo: {
      homeProb: 0.48,
      drawProb: 0.28,
      awayProb: 0.24,
      weight: 0.25,
    },
    xg: {
      homeProb: 0.46,
      drawProb: 0.26,
      awayProb: 0.28,
      weight: 0.25,
    },
    xgboost: {
      homeProb: 0.49,
      drawProb: 0.29,
      awayProb: 0.22,
      weight: 0.25,
    },
  },
  llmAdjustments: {
    injuryImpactHome: -0.02,
    injuryImpactAway: -0.04,
    sentimentHome: 0.03,
    sentimentAway: -0.02,
    tacticalEdge: 0.04,
    totalAdjustment: 0.05,
    reasoning:
      "Liverpool's tactical weakness away from home combined with United's home advantage and recent good form provides value. However, recent injury concerns for both teams slightly reduce confidence.",
  },
  expectedHomeGoals: 2.3,
  expectedAwayGoals: 1.8,
  createdAt: new Date().toISOString(),
};

/**
 * Mock team form data
 */
export const mockHomeTeamForm: TeamForm = {
  teamId: 1,
  teamName: "Manchester United",
  lastMatches: [
    {
      id: 101,
      homeTeam: "Manchester United",
      awayTeam: "Aston Villa",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 3,
      awayScore: 1,
    },
    {
      id: 102,
      homeTeam: "Wolverhampton",
      awayTeam: "Manchester United",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 1,
      awayScore: 2,
    },
    {
      id: 103,
      homeTeam: "Manchester United",
      awayTeam: "Chelsea",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 2,
      awayScore: 0,
    },
    {
      id: 104,
      homeTeam: "Brighton",
      awayTeam: "Manchester United",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 17 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 0,
      awayScore: 1,
    },
    {
      id: 105,
      homeTeam: "Manchester United",
      awayTeam: "Nottingham Forest",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 21 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 3,
      awayScore: 0,
    },
  ],
  formString: "VVVVV",
  pointsLast5: 15,
  goalsScoredAvg: 2.6,
  goalsConcededAvg: 0.4,
  cleanSheets: 4,
  xgForAvg: 2.45,
  xgAgainstAvg: 0.85,
};

export const mockAwayTeamForm: TeamForm = {
  teamId: 2,
  teamName: "Liverpool",
  lastMatches: [
    {
      id: 201,
      homeTeam: "Liverpool",
      awayTeam: "Bournemouth",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 2,
      awayScore: 1,
    },
    {
      id: 202,
      homeTeam: "Crystal Palace",
      awayTeam: "Liverpool",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 1,
      awayScore: 1,
    },
    {
      id: 203,
      homeTeam: "Liverpool",
      awayTeam: "Manchester City",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 3,
      awayScore: 1,
    },
    {
      id: 204,
      homeTeam: "Newcastle United",
      awayTeam: "Liverpool",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 17 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 2,
      awayScore: 0,
    },
    {
      id: 205,
      homeTeam: "Liverpool",
      awayTeam: "Everton",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 21 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 2,
      awayScore: 1,
    },
  ],
  formString: "VDVDV",
  pointsLast5: 11,
  goalsScoredAvg: 2.2,
  goalsConcededAvg: 0.8,
  cleanSheets: 1,
  xgForAvg: 2.15,
  xgAgainstAvg: 1.2,
};

/**
 * Mock head-to-head data
 */
export const mockHeadToHead = {
  matches: [
    {
      id: 301,
      homeTeam: "Manchester United",
      awayTeam: "Liverpool",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 2,
      awayScore: 1,
    },
    {
      id: 302,
      homeTeam: "Liverpool",
      awayTeam: "Manchester United",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 350 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 2,
      awayScore: 2,
    },
    {
      id: 303,
      homeTeam: "Manchester United",
      awayTeam: "Liverpool",
      competition: "Premier League",
      competitionCode: "PL",
      matchDate: new Date(Date.now() - 200 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 1,
      awayScore: 0,
    },
    {
      id: 304,
      homeTeam: "Liverpool",
      awayTeam: "Manchester United",
      competition: "FA Cup",
      competitionCode: "FC",
      matchDate: new Date(Date.now() - 150 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 2,
      awayScore: 2,
    },
    {
      id: 305,
      homeTeam: "Manchester United",
      awayTeam: "Liverpool",
      competition: "League Cup",
      competitionCode: "LC",
      matchDate: new Date(Date.now() - 100 * 24 * 60 * 60 * 1000).toISOString(),
      status: "finished",
      homeScore: 3,
      awayScore: 1,
    },
  ],
  homeWins: 3,
  draws: 2,
  awayWins: 2,
};

/**
 * Mock matches for upcoming matches list
 */
export const mockUpcomingMatches: Match[] = [
  {
    id: 1,
    homeTeam: "Manchester United",
    awayTeam: "Liverpool",
    competition: "Premier League",
    competitionCode: "PL",
    matchDate: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    status: "scheduled",
    matchday: 20,
  },
  {
    id: 2,
    homeTeam: "Manchester City",
    awayTeam: "Arsenal",
    competition: "Premier League",
    competitionCode: "PL",
    matchDate: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    status: "scheduled",
    matchday: 20,
  },
  {
    id: 3,
    homeTeam: "Real Madrid",
    awayTeam: "Barcelona",
    competition: "La Liga",
    competitionCode: "LL",
    matchDate: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
    status: "scheduled",
    matchday: 19,
  },
  {
    id: 4,
    homeTeam: "Paris Saint-Germain",
    awayTeam: "Marseille",
    competition: "Ligue 1",
    competitionCode: "L1",
    matchDate: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
    status: "scheduled",
    matchday: 18,
  },
];

/**
 * Get mock data by ID
 */
export function getMockMatchById(id: number): Match {
  const matches = [mockMatch, ...mockUpcomingMatches];
  return matches.find((m) => m.id === id) || mockMatch;
}

/**
 * Hook to use mock data in development
 * Set NEXT_PUBLIC_USE_MOCK_DATA=true in your .env.local
 */
export const useMockData = () => {
  return process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true";
};
