package EcoGrid.dao;

import EcoGrid.entity.Demandageneracionree;
import org.springframework.data.jpa.repository.JpaRepository;
import java.time.LocalDateTime;
import java.time.Instant;
import java.util.List;

public interface DemandageneracionreeRepository
        extends JpaRepository<Demandageneracionree, Long> {

    List<Demandageneracionree>
    findByIdccaa_IdAndIdtiempo_FechoraBetweenOrderByIdtiempo_FechoraAsc(
            Long idccaa, LocalDateTime desde, LocalDateTime hasta);
}