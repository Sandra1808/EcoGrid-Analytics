package EcoGrid.dao;

import EcoGrid.entity.Tiempohorario;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TiempohorarioRepository
        extends JpaRepository<Tiempohorario, Long> {
}