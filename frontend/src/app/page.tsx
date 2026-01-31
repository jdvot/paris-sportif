import { DailyPicks } from "@/components/DailyPicks";
import { UpcomingMatches } from "@/components/UpcomingMatches";
import { StatsOverview } from "@/components/StatsOverview";
import { TrendingUp, Calendar, Trophy } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <section className="text-center py-8">
        <h1 className="text-4xl font-bold text-white mb-4">
          Predictions Football IA
        </h1>
        <p className="text-dark-300 text-lg max-w-2xl mx-auto">
          Analyse statistique avancee combinant modeles Poisson, ELO, xG et
          machine learning pour identifier les meilleures opportunites de paris
          sur le football europeen.
        </p>
      </section>

      {/* Quick Stats */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 flex items-center gap-4">
          <div className="p-3 bg-primary-500/20 rounded-lg">
            <TrendingUp className="w-6 h-6 text-primary-400" />
          </div>
          <div>
            <p className="text-dark-400 text-sm">Taux de reussite</p>
            <p className="text-2xl font-bold text-white">62.5%</p>
          </div>
        </div>
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 flex items-center gap-4">
          <div className="p-3 bg-accent-500/20 rounded-lg">
            <Calendar className="w-6 h-6 text-accent-400" />
          </div>
          <div>
            <p className="text-dark-400 text-sm">Matchs analyses/jour</p>
            <p className="text-2xl font-bold text-white">45+</p>
          </div>
        </div>
        <div className="bg-dark-800/50 border border-dark-700 rounded-xl p-6 flex items-center gap-4">
          <div className="p-3 bg-yellow-500/20 rounded-lg">
            <Trophy className="w-6 h-6 text-yellow-400" />
          </div>
          <div>
            <p className="text-dark-400 text-sm">Championnats couverts</p>
            <p className="text-2xl font-bold text-white">7</p>
          </div>
        </div>
      </section>

      {/* Daily Picks */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">
            5 Picks du Jour
          </h2>
          <span className="text-dark-400 text-sm">
            Mis a jour: {new Date().toLocaleDateString("fr-FR")}
          </span>
        </div>
        <DailyPicks />
      </section>

      {/* Upcoming Matches */}
      <section>
        <h2 className="text-2xl font-bold text-white mb-6">
          Matchs a Venir
        </h2>
        <UpcomingMatches />
      </section>

      {/* Stats Overview */}
      <section>
        <h2 className="text-2xl font-bold text-white mb-6">
          Performance des Predictions
        </h2>
        <StatsOverview />
      </section>
    </div>
  );
}
